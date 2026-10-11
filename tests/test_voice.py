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
