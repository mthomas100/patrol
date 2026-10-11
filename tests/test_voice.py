"""Offline tests of voice routing: Clef's answer gated by probability, and the keyword fallback when Clef fails."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from patrol import voice  # noqa: E402
from patrol.clef import Decision  # noqa: E402


def fake_ask(decision):
    return lambda *a, **k: decision


def test_confident_route_becomes_a_command(monkeypatch):
    d = Decision(ok=True, action="change_target", probs={"change_target": 0.8, "none": 0.2}, extra={"phase": "far"})
    monkeypatch.setattr(voice.clef, "ask", fake_ask(d))
    r = voice.route("look at the far wire")
    assert r["ok"] and r["source"] == "CLEF" and r["command"] == {"name": "change_target", "phase": "far"}


def test_unsure_or_none_route_is_not_executed(monkeypatch):
    monkeypatch.setattr(voice.clef, "ask", fake_ask(Decision(ok=True, action="return_home",
                                                             probs={"return_home": 0.40, "question": 0.35})))
    assert not voice.route("hmm home maybe").get("command")
    monkeypatch.setattr(voice.clef, "ask", fake_ask(Decision(ok=True, action="none", probs={"none": 0.9})))
    assert not voice.route("nice weather").get("command")


def test_failed_clef_falls_back_to_keywords(monkeypatch):
    monkeypatch.setattr(voice.clef, "ask", fake_ask(Decision(ok=False, error="URLError: refused")))
    r = voice.route("Patrol, return home now.")
    assert r["source"] == "FALLBACK" and r["command"] == {"name": "return_home"}
    r = voice.route("what is the battery level")
    assert r["source"] == "FALLBACK" and not r.get("command")


def test_search_routes_use_the_search_command_set(monkeypatch):
    seen = {}

    def ask(images, state, questions, **k):
        seen["criteria"] = questions["action"]["criteria"]
        seen["state"] = state
        return Decision(ok=True, action="go_back_to_last_alert", probs={"go_back_to_last_alert": 0.9})
    monkeypatch.setattr(voice.clef, "ask", ask)
    r = voice.route("go back to the last alert", kind="search")
    assert r["command"] == {"name": "go_back_to_last_alert"}
    assert "describe" in seen["criteria"] and "change_target" not in seen["criteria"]
    assert "search-and-rescue" in seen["state"]
    monkeypatch.setattr(voice.clef, "ask", fake_ask(Decision(ok=False, error="URLError: refused")))
    assert voice.route("Missing hiker. Blue backpack, orange tent.", kind="search")["command"] == {"name": "describe"}
    assert voice.route("Stop searching and come home.", kind="search")["command"] == {"name": "return_home"}


class _Rec(voice.Speaker):
    """A Speaker that records what it would say (no voice worker)."""
    def __init__(self):
        self.said = []

    def say(self, key, text, **extra):
        self.said.append((key, text))


def test_search_speaker_reads_alerts_once():
    alert = {"type": "alert", "id": "A1", "family": "blue backpack", "g": [34.3, -25.8]}
    note = {"type": "note", "id": "A1", "alert": "Blue backpack spotted east of centre.", "check": "Walk in and look."}
    for think, want in ((False, ["alert_A1"]), (True, ["note_A1"])):
        rec = _Rec()
        rec({"type": "start", "spec": {"kind": "search"}, "config": {"thinker": think}})
        rec(alert)
        if think:
            rec(note)
        assert [k for k, _ in rec.said] == want
    assert "34 metres east and 26 metres south" in voice.alert_text(alert)
    rec = _Rec()      # a failed note falls back to the alert's own words
    rec({"type": "start", "spec": {"kind": "search"}, "config": {"thinker": True}})
    rec(alert)
    rec({"type": "note", "id": "A1", "error": "HTTP 503"})
    assert rec.said == [("note_A1", voice.alert_text(alert))]


# ------------------------------------------------------------------ acknowledge what the mission did (patrol-ab)
class Said:
    def __init__(self):
        self.lines = []

    def say(self, key, text):
        self.lines.append(text)


class Heard:
    def __init__(self, text):
        self.text = text

    def stt(self, wav):
        return {"ok": True, "text": self.text, "stt_ms": 1}


def search_mission(tmp_path):
    from patrol import clues, search, world
    cfg = search.SearchConfig(W=320, H=240)
    spec = world.search_spec(3, "snow", [], size=200.0, n_rocks=10, n_trees=4)
    return search.SearchMission(spec, tmp_path, clues.clues(["blue_backpack"]), cfg, realtime=False,
                                save_frames=False, ask=lambda *a, **k: Decision(ok=False, error="offline"))


def say_to(m, monkeypatch, name):
    """Route one utterance to `name` and let the mission tick on its own thread, as in a flight."""
    import threading
    monkeypatch.setattr(voice, "route", lambda *a, **k: {"command": {"name": name}, "name": name, "p": 0.9,
                                                         "probs": {name: 0.9}, "source": "CLEF", "ms": 1})
    stop, sp = threading.Event(), Said()
    t = threading.Thread(target=lambda: [m.tick() for _ in iter(lambda: stop.is_set(), True)], daemon=True)
    t.start()
    voice.handle_utterance("x.wav", Heard("go back"), m, speaker=sp)
    stop.set(); t.join(2)
    return sp.lines


def test_a_refused_command_is_not_acknowledged_as_taken(tmp_path, monkeypatch):
    m = search_mission(tmp_path)
    events = []
    m.sinks.append(events.append)
    assert say_to(m, monkeypatch, "go_back_to_last_alert") == ["I can't do that now: there is no alert yet."]
    op = [e for e in events if e["type"] == "operator"][-1]
    assert op["accepted"] is False and "_reply" not in op["command"]


def test_a_taken_command_is_acknowledged(tmp_path, monkeypatch):
    m = search_mission(tmp_path)
    assert say_to(m, monkeypatch, "return_home") == ["Returning home."]
    assert m.state in ("RETURN", "DONE") and m.return_reason == "operator: return home"


def test_go_back_while_investigating_is_the_next_spot(tmp_path):
    m = search_mission(tmp_path)
    m.alerts = [{"id": "A1", "g": [30.0, 30.0], "clue": "blue_backpack", "conf": 0.9, "sweep_crop": None,
                 "sweep_h": 40.0}]
    m.state, m.spot = "INVESTIGATE", {"id": "S4"}
    m.pending = [{"g": (1.0, 1.0), "clue": "blue_backpack"}]           # a nearer ordinary spot waiting
    said = []
    m._operator({"name": "go_back_to_last_alert", "_reply": lambda ok, why: said.append((ok, why))})
    assert said == [(True, "after the spot being checked (S4)")]
    m._next_spot()
    assert m.spot.get("revisit") == "A1"
