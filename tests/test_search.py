"""Search loop: safety helpers, the full state path with a scripted Clef, and the ground-truth leak test.

The leak test (BRIEF, testing doctrine) fails if anything on the decision path reads the planted items, the clutter
positions, segmentation or geom names: the runtime half poisons every source of truth after the mission is built and
flies a whole small search through SWEEP, INVESTIGATE, CONFIRM, ALERT, RESUME and RETURN; the static half checks the
decision-path source for the calls that would read truth.
"""
from __future__ import annotations

import ast
import inspect
import json
import textwrap

import pytest

from patrol import anomaly, clef, clues, geo, planner, search, world
from patrol.sim import Sim


class Poison(list):
    def _boom(self, *a, **k):
        raise AssertionError("ground truth read on the decision path")
    __iter__ = __getitem__ = __len__ = __contains__ = __bool__ = _boom


def fake_clef(verdicts):
    """A scripted Clef: every fourth sweep crop is a strong 'investigate'; confirms follow `verdicts` in turn."""
    calls = {"sweep": 0, "confirm": 0}

    def ask(jpeg, state, questions, timeout=6.0, url=""):
        name = next(k for k, v in questions.items() if v["type"] == "noul")
        if "investigate" in questions["action"]["criteria"]:
            calls["sweep"] += 1
            if calls["sweep"] % 4 == 1:
                return clef.Decision(ok=True, action="investigate", probs={"investigate": 0.8, "continue": 0.2},
                                     nouls={name: 0.7}, latency_ms=1.0)
            return clef.Decision(ok=True, action="continue", probs={"investigate": 0.05, "continue": 0.95},
                                 nouls={name: 0.02}, latency_ms=1.0)
        v = verdicts[calls["confirm"] % len(verdicts)]
        calls["confirm"] += 1
        if v == "confirm":
            return clef.Decision(ok=True, action=name, probs={name: 0.9}, nouls={name: 0.9}, latency_ms=1.0)
        return clef.Decision(ok=True, action="other", probs={"other": 0.9}, nouls={name: 0.05}, latency_ms=1.0)
    ask.calls = calls
    return ask


def small_mission(tmp_path, ask, items=None):
    h = 30.0
    cfg = search.SearchConfig(area=[(-h, -h), (h, -h), (h, h), (-h, h)], home=(0.0, -h - 10, 2.0), sweep_h=40.0,
                              W=320, H=240, frame_every_m=12.0)
    spec = world.search_spec(3, "snow", items or [], size=100.0, n_rocks=30, n_trees=8)
    events = []
    m = search.SearchMission(spec, tmp_path, clues.clues(["blue_backpack"]), cfg, sinks=[events.append],
                             realtime=False, save_frames=False, ask=ask)
    return m, spec, events


def test_outside_by():
    sq = [(-10, -10), (10, -10), (10, 10), (-10, 10)]
    assert search.outside_by(sq, 0, 0) == 0.0
    assert search.outside_by(sq, 15, 0) == pytest.approx(5.0)
    assert search.outside_by(list(reversed(sq)), 0, -13) == pytest.approx(3.0)


def test_full_state_path_without_ground_truth(tmp_path, monkeypatch):
    ask = fake_clef(["dismiss", "confirm"])
    m, spec, events = small_mission(tmp_path, ask)
    # poison every source of truth after construction: the decision path must never touch them
    for k in search.TRUTH_KEYS:
        spec[k] = Poison()
    assert not set(search.TRUTH_KEYS) & set(m.spec) and m.sim.spec is m.spec
    for meth in ("project", "visible_defects", "vegetation_clearance"):
        monkeypatch.setattr(Sim, meth, lambda *a, **k: (_ for _ in ()).throw(AssertionError("truth via Sim")))
    s = m.run(max_ticks=3000)
    types = {e["type"] for e in events}
    states = {e["state"] for e in events if e["type"] == "state"}
    assert s["state"] == "DONE" and s["return_reason"] == "area covered"
    assert {"frame", "investigate", "confirm", "dismiss", "alert"} <= types
    assert {"SWEEP", "INVESTIGATE", "RESUME", "RETURN", "DONE"} <= states
    assert s["coverage"] > 0.95
    alerts = [e for e in events if e["type"] == "alert"]
    # one alert per spot: each confirmed spot alerts once, and nothing within alert_r of it alerts again
    for i, a in enumerate(alerts):
        assert all(((a["g"][0] - b["g"][0]) ** 2 + (a["g"][1] - b["g"][1]) ** 2) ** 0.5 >= m.cfg.alert_r
                   for b in alerts[i + 1:])
    json.dumps(events)    # every event is loggable


def test_clef_dead_finishes_on_fallback(tmp_path):
    def dead(jpeg, state, questions, timeout=6.0, url=""):
        return clef.Decision(ok=False, error="URLError: connection refused", latency_ms=2.0)
    m, _, events = small_mission(tmp_path, dead)
    s = m.run(max_ticks=3000)
    assert s["state"] == "DONE" and s["return_reason"] == "area covered"
    assert s["alerts"] == [] and s["investigations"] == 0 and s["fallback"] > 0


def test_operator_return_home(tmp_path):
    m, _, events = small_mission(tmp_path, fake_clef(["dismiss"]))
    s = m.run(max_ticks=3000, script={60: {"name": "return_home"}})
    assert s["state"] == "DONE" and s["return_reason"] == "operator: return home" and s["coverage"] < 0.9


def code_only(obj) -> str:
    """Source without docstrings or comments (they may say what the code does not use)."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(obj)))
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr) \
                and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            node.body = body[1:] or [ast.Pass()]
    return ast.unparse(tree)


def test_decision_path_source_reads_no_truth():
    forbidden = ("'items'", "segmentation", ".geom(", "geom_", "project(", "visible_defects",
                 "vegetation_clearance", "json.loads", "scene.json').read")
    src = "".join(code_only(o) for o in (search.SearchMission, anomaly, geo, planner, clues))
    hits = [f for f in forbidden if f in src]
    assert not hits, f"decision path mentions {hits}"


def test_a_much_better_view_of_a_judged_spot_is_asked_again(tmp_path, monkeypatch):
    """runs/s3-trail-ab-rt grass6: a 60 px glimpse at a frame's far side, judged 'continue', hid the backpack's clear
    241 px view a lane later (same spot within judged_r), and the clue was never investigated."""
    asked = []

    def ask(jpeg, state, questions, timeout=6.0, url=""):
        asked.append(1)
        name = next(k for k, v in questions.items() if v["type"] == "noul")
        return clef.Decision(ok=True, action="continue", probs={"continue": 0.9}, nouls={name: 0.01}, latency_ms=1.0)
    m, spec, events = small_mission(tmp_path, ask)
    views = iter([(60, (2.68, -31.16)), (241, (1.89, -28.34)), (300, (1.79, -28.34)), (900, (1.8, -28.3)),
                  (2000, (1.8, -28.3))])
    cur = {}

    def candidates(jpg, k=3):
        area, g = next(views)
        cur["g"] = g
        return [{"x0": 100, "y0": 100, "x1": 120, "y1": 120, "cx": 110, "cy": 110, "score": 1.0, "area": area}]
    monkeypatch.setattr(search.anomaly, "candidates", candidates)
    orig = search.geo.pixel_to_ground          # the footprint uses it too: fake only the candidate's pixel
    monkeypatch.setattr(search.geo, "pixel_to_ground",
                        lambda u, v, *a, **k: cur["g"] if (u, v) == (110, 110) else orig(u, v, *a, **k))
    lane = {"x0": -30.0, "x1": 30.0, "y": -28.0}
    status = []
    for _ in range(5):
        m._sweep_frame(lane)
        status.append(events[-1]["candidates"][0]["status"])
    # glimpse judged; 4x larger view judged again; 1.2x not; 3x judged (third ask); max_asks reached after that
    assert status == ["judged", "judged", "seen", "judged", "seen"]
    assert len(asked) == 3 and len(m.judged) == 1 and m.judged[0]["asks"] == 3


def test_edge_boxes_are_judged_at_once(tmp_path, monkeypatch):
    """Deferring a box cut by the frame edge to a neighbouring frame lost it more often than not (558 of 960 on tuning
    flights were never judged; a bottom-edge box is behind the drone for good): edge boxes are judged at once."""
    m, spec, events = small_mission(tmp_path, fake_clef(["dismiss"]))
    W, H = m.cfg.W, m.cfg.H
    boxes = iter([(100, 2, 120, 22), (100, H - 22, 120, H - 2)])

    def candidates(jpg, k=3):
        x0, y0, x1, y1 = next(boxes)
        return [{"x0": x0, "y0": y0, "x1": x1, "y1": y1, "cx": (x0 + x1) / 2, "cy": (y0 + y1) / 2, "score": 1.0,
                 "area": 300}]
    monkeypatch.setattr(search.anomaly, "candidates", candidates)
    lane = {"x0": -30.0, "x1": 30.0, "y": -28.0}
    m._sweep_frame(lane)
    m.judged.clear()                    # the drone sits low at home here: keep the two boxes separate spots
    m._sweep_frame(lane)
    st = [e["candidates"][0]["status"] for e in events if e["type"] == "frame"]
    assert st == ["judged", "judged"], st
    assert all(e["candidates"][0].get("edge") for e in events if e["type"] == "frame")


def test_a_flown_spot_blocks_only_the_ground_its_close_up_covered(tmp_path, monkeypatch):
    """runs/s5-live-test1: a background spot framed for a backpack (close-up about 4 m across) was dismissed, and the
    tent 3.8 m away, judged 'investigate' a lane later, was never flown to (the old dedupe radius was 6 m)."""
    def ask(jpeg, state, questions, timeout=6.0, url=""):
        name = next(k for k, v in questions.items() if v["type"] == "noul")
        return clef.Decision(ok=True, action="investigate", probs={"investigate": 0.8}, nouls={name: 0.3},
                             latency_ms=1.0)
    m, spec, events = small_mission(tmp_path, ask)
    m.investigated = [{"g": (10.33, 14.99), "cover_r": 2.0, "id": "S1"}]
    m.state = "SWEEP"
    m.cur = {"x0": -30.0, "x1": 30.0, "y": 18.0, "lane": 0, "id": "A1"}

    def candidates(jpg, k=3):
        return [{"x0": 100, "y0": 100, "x1": 140, "y1": 140, "cx": 120, "cy": 120, "score": 1.0, "area": 1600}]
    monkeypatch.setattr(search.anomaly, "candidates", candidates)
    orig = search.geo.pixel_to_ground
    monkeypatch.setattr(search.geo, "pixel_to_ground",
                        lambda u, v, *a, **k: (11.21, 18.56) if (u, v) == (120, 120) else orig(u, v, *a, **k))
    m._sweep_frame(m.cur)
    assert [s["g"] for s in m.investigated][1:] == [(11.21, 18.56)]
