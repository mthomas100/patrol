"""Offline tests of the gate, fallback policy and state machine (no MuJoCo, no models)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from patrol.clef import Decision  # noqa: E402
from patrol.control import (ACTIONS, CONFIRM_WEIGHTS, CRUISE_WEIGHTS, Config, StateMachine, Target,  # noqa: E402
                            gate)


def dec(**probs):
    return Decision(ok=True, action=max(probs, key=probs.get), probs=probs, confidence=max(probs.values()),
                    sure=1.3, latency_ms=400)


def test_failed_decision_is_fallback():
    g = gate(Decision(ok=False, error="boom"), ACTIONS, CRUISE_WEIGHTS, "continue", "protocol")
    assert g.label == "FALLBACK" and g.action == "continue" and "failed" in g.reason


def test_late_decision_is_fallback():
    d = dec(**{"continue": 0.9, "hover_and_photograph": 0.05, "go_back": 0.03, "flag_damage": 0.02})
    d.latency_ms = 9000
    assert gate(d, ACTIONS, CRUISE_WEIGHTS, "continue", "p").label == "FALLBACK"
    assert gate(d, ACTIONS, CRUISE_WEIGHTS, "continue", "p", deadline_ms=10000).label == "CLEF"


def test_unsure_decision_is_fallback():
    d = dec(**{"continue": 0.28, "hover_and_photograph": 0.27, "go_back": 0.25, "flag_damage": 0.2})
    assert gate(d, ACTIONS, CRUISE_WEIGHTS, "continue", "p").label == "FALLBACK"
    d = dec(**{"continue": 0.9, "hover_and_photograph": 0.05, "go_back": 0.03, "flag_damage": 0.02})
    d.sure = 0.2
    assert gate(d, ACTIONS, CRUISE_WEIGHTS, "continue", "p").label == "FALLBACK"


def test_cost_weights_turn_a_suspicion_into_a_hover():
    d = dec(**{"continue": 0.42, "hover_and_photograph": 0.30, "go_back": 0.18, "flag_damage": 0.10})
    g = gate(d, ACTIONS, CRUISE_WEIGHTS, "continue", "p")
    assert g.label == "CLEF" and g.action == "hover_and_photograph"
    clean = dec(**{"continue": 0.58, "hover_and_photograph": 0.20, "go_back": 0.16, "flag_damage": 0.06})
    assert gate(clean, ACTIONS, CRUISE_WEIGHTS, "continue", "p").action == "continue"


def test_confirm_flags_above_a_quarter():
    assert gate(dec(flag_damage=0.44, **{"continue": 0.56}), ("continue", "flag_damage"), CONFIRM_WEIGHTS,
                "continue", "p").action == "flag_damage"
    assert gate(dec(flag_damage=0.05, **{"continue": 0.95}), ("continue", "flag_damage"), CONFIRM_WEIGHTS,
                "continue", "p").action == "continue"


def test_hover_then_settled_spot_is_not_rephotographed():
    sm = StateMachine(Config())
    t = Target(100, -4.5, 13.1)
    d = dec(**{"continue": 0.4, "hover_and_photograph": 0.35, "go_back": 0.15, "flag_damage": 0.1})
    g = sm.on_cruise(gate(d, ACTIONS, CRUISE_WEIGHTS, "continue", "p"), t, d)
    assert sm.state == "HOVER" and g.action == "hover_and_photograph"
    sm.on_confirm(gate(dec(flag_damage=0.05, **{"continue": 0.95}), ("continue", "flag_damage"), CONFIRM_WEIGHTS,
                       "continue", "p"))
    assert sm.state == "CRUISE"
    g = sm.on_cruise(gate(d, ACTIONS, CRUISE_WEIGHTS, "continue", "p"), Target(102, -4.5, 13.1), d)
    assert g.action == "continue" and "already photographed" in g.reason


def test_unconfirmed_photo_allows_one_more_look():
    sm = StateMachine(Config())
    sm.target = Target(100, -4.5, 13.1); sm.state = "HOVER"
    sm.on_confirm(gate(Decision(ok=False, error="late"), ("continue", "flag_damage"), CONFIRM_WEIGHTS,
                       "continue", "p"))
    d = dec(**{"continue": 0.4, "hover_and_photograph": 0.35, "go_back": 0.15, "flag_damage": 0.1})
    sm.on_cruise(gate(d, ACTIONS, CRUISE_WEIGHTS, "continue", "p"), Target(101, -4.5, 13.1), d)
    assert sm.state == "HOVER"


def test_go_back_needs_a_suspect():
    sm = StateMachine(Config())
    d = dec(**{"continue": 0.2, "hover_and_photograph": 0.1, "go_back": 0.6, "flag_damage": 0.1})
    g = sm.on_cruise(gate(d, ACTIONS, CRUISE_WEIGHTS, "continue", "p"), Target(50, -4.5, 12), d)
    assert g.action == "continue" and "nothing" in g.reason
    sm.suspect = (0.5, Target(40, -4.5, 12))
    g = sm.on_cruise(gate(d, ACTIONS, CRUISE_WEIGHTS, "continue", "p"), Target(55, -4.5, 12), d)
    assert sm.state == "REVISIT" and sm.target.x == 40


def test_safety_battery_and_corridor_end():
    sm = StateMachine(Config(battery_start=7.0))
    g = sm.safety((150, -12, 13), 3.0)
    assert g.label == "SAFETY" and sm.state == "RETURN" and "battery" in g.reason
    sm = StateMachine(Config())
    assert sm.safety((310, -12, 13), 3.0).label == "SAFETY" and sm.corridor_done


def test_fallback_protocol_photographs_each_tower_once():
    sm = StateMachine(Config())
    t = Target(100, -4.5, 13.1)
    assert sm.fallback_cruise(90, t, True)[0] == "hover_and_photograph"
    sm.photographed.append(t)
    assert sm.fallback_cruise(92, t, True)[0] == "continue"
    assert sm.fallback_cruise(120, Target(129, -4.5, 12), False)[0] == "continue"


def test_operator_commands():
    sm = StateMachine(Config())
    assert sm.operator({"name": "return_home"}).label == "OPERATOR" and sm.state == "RETURN"
    sm = StateMachine(Config())
    assert sm.operator({"name": "revisit_last_flag"}) is None     # nothing flagged yet
    assert sm.operator({"name": "change_target", "phase": "middle"}).label == "OPERATOR" and sm.phase == "middle"


def test_speed_governor():
    sm = StateMachine(Config())
    assert sm.governed_cruise(0.45) == 3.0
    assert abs(sm.governed_cruise(1.0) - 1.6) < 1e-9
    assert sm.governed_cruise(10) == 0.8
