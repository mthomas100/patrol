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


def test_confirm_gate_corroboration():
    """runs/s4-e2e-4 F7: p(flag) 0.37 with every component answer <= 0.06 was a false alarm; F3 (0.35) was real."""
    from patrol.control import confirm_gate
    d = dec(flag_damage=0.37, **{"continue": 0.63})
    d.nouls = {"insulator_damaged": 0.015, "conductor_frayed": 0.017, "vegetation_close": 0.047, "foreign_object": 0.062}
    g = confirm_gate(d, "p")
    assert g.action == "continue" and "uncorroborated" in g.reason
    d.nouls = {"insulator_damaged": 0.18, "foreign_object": 0.35}
    assert confirm_gate(d, "p").action == "flag_damage"
    d.nouls = {}                                                      # no component answers: p(flag) decides
    assert confirm_gate(d, "p").action == "flag_damage"


def test_confirm_gate_noul_upgrade():
    from patrol.control import confirm_gate
    d = dec(flag_damage=0.22, **{"continue": 0.78}); d.nouls = {"foreign_object": 0.5, "vegetation_close": 0.1}
    g = confirm_gate(d, "p")
    assert g.action == "flag_damage" and "foreign_object" in g.reason
    d.nouls = {"foreign_object": 0.05, "vegetation_close": 0.58}       # perspective false positive stays clean
    assert confirm_gate(d, "p").action == "continue"
    assert confirm_gate(Decision(ok=False, error="x"), "p").label == "FALLBACK"


def test_staleness_by_distance_flown():
    d = dec(**{"continue": 0.3, "hover_and_photograph": 0.4, "go_back": 0.2, "flag_damage": 0.1})
    d.latency_ms = 4000
    assert gate(d, ACTIONS, CRUISE_WEIGHTS, "continue", "p", moved_m=3.2).label == "CLEF"    # slow but governed
    g = gate(d, ACTIONS, CRUISE_WEIGHTS, "continue", "p", moved_m=5.0)
    assert g.label == "FALLBACK" and "stale" in g.reason


def _rf(near, middle=9.0, far=9.0, x=120.0):
    return {ph: {"clearance": c, "x": x, "y": y, "z": 11.8}
            for ph, c, y in (("near", near, -4.5), ("middle", middle, 0.0), ("far", far, 4.5))}


def test_rangefinder_hovers_on_an_encroaching_tree_once():
    from patrol.control import rangefinder_flag
    sm = StateMachine(Config())
    assert sm.on_rangefinder(_rf(6.0), 110) is None and sm.state == "CRUISE"       # healthy tree: keep flying
    assert sm.on_rangefinder(_rf(0.2, x=140), 110) is None                         # too far ahead to photograph
    g = sm.on_rangefinder(_rf(0.2, middle=0.1), 110)
    assert g.label == "RANGEFINDER" and sm.state == "HOVER"
    assert sm.target.y == -4.5          # the inspected phase wins when it is itself within the trigger distance
    photo = gate(dec(flag_damage=0.05, **{"continue": 0.95}), ("continue", "flag_damage"), CONFIRM_WEIGHTS,
                 "continue", "p")
    g = rangefinder_flag(photo, 0.2)
    assert g.action == "flag_damage" and g.label == "RANGEFINDER"
    sm.on_confirm(g)
    assert sm.state == "CRUISE" and sm.on_rangefinder(_rf(0.2, x=121), 112) is None   # settled: no second hover


def test_rangefinder_flag_leaves_clear_trees_to_the_photo():
    from patrol.control import rangefinder_flag
    photo = gate(dec(flag_damage=0.05, **{"continue": 0.95}), ("continue", "flag_damage"), CONFIRM_WEIGHTS,
                 "continue", "p")
    assert rangefinder_flag(photo, 1.4).action == "continue"
    assert rangefinder_flag(photo, None).action == "continue"


def test_silence_is_never_a_command():
    """An empty transcript (a tap on push-to-talk) must not reach the router: Clef sent "" to start_search at p 0.95."""
    from patrol import voice

    class W:
        def __init__(self, text): self.text = text
        def stt(self, wav): return {"ok": True, "text": self.text}

    class M:
        alerts, ticks, events = [], 0, []
        def emit(self, kind, **kw): self.events.append((kind, kw)); return kw
        def status_text(self): return ""

    for text in ("", "  ", ".", "a"):
        m = M(); m.events = []
        ev = voice.handle_utterance("x.wav", W(text), m, url="http://127.0.0.1:9/v1/systemone")
        assert ev["accepted"] is False and ev["error"] == "nothing heard"
