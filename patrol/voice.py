"""Operator voice: speech in (Parakeet) -> Clef-Flash routes the words to a drone command -> Mission.command();
notes and answers out through Kokoro. The speech models live in one worker process (patrol/voice_worker.py, run
with local-voice's venv); routing is one Clef call with no image.

Two command sets: the power-line corridor (COMMANDS) and the search (SEARCH_COMMANDS: start, go back to the last
alert, return home, a description of what to look for, a question). A spoken description goes to qwen38
(thinker.describe), which turns it into clue options.
"""
from __future__ import annotations

import json
import queue
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import clef

ROOT = Path(__file__).resolve().parents[1]
LV_PY = Path.home() / "repos/local-voice/orchestrator/.venv/bin/python"

COMMANDS = {
    "start_mission": "start the inspection flight, take off, begin the patrol",
    "revisit_last_flag": "go back to the last flagged spot or the damage just found and look at it again, re-inspect "
                         "or re-photograph it",
    "return_home": "stop the patrol and fly back to the launch point, come home, land, abort",
    "change_target": "inspect a different conductor phase: the near, middle or far wire",
    "question": "the operator asks a question about the mission, the damage found, the battery or the drone's status",
    "none": "not a request to the drone: noise, chatter to someone else, or words that ask for nothing",
}
PHASES = {"near": "the near phase, the wire closest to the drone", "middle": "the middle phase, the centre wire",
          "far": "the far phase, the wire furthest from the drone"}
SEARCH_COMMANDS = {
    "start_search": "start the search flight: take off and begin searching the area",
    "go_back_to_last_alert": "go back to the last alert or the last thing the drone found and look at it again",
    "return_home": "stop searching and fly back to the launch point: come home, land, abort",
    "describe": "the operator describes the missing person or what they had with them (a bag, a tent, clothing, a "
                "pet, their colours) so the drone knows what to look for",
    "question": "the operator asks a question about the search, what was found, the battery or the drone's status",
    "none": "not a request to the drone: noise, chatter to someone else, or words that ask for nothing",
}
ROUTE_MIN_P = 0.45          # below this the command is not executed and the console says it was not understood

# Deterministic fallback, used only when Clef fails to answer (never when it answers unsure): the same honest
# FALLBACK the flight loop uses, so "return home" still works with the decision model down.
KEYWORDS = [
    ("return_home", r"\b(return|come|go|fly|head)\b.*\bhome\b|\babort\b|\bland\b"),
    ("revisit_last_flag", r"\bgo back\b|\blook again\b|\bagain\b|\brevisit\b|\bre-?inspect\b"),
    ("change_target", r"\b(near|middle|centre|center|far)\b.*\b(phase|wire|conductor|line)\b"),
    ("start_mission", r"\b(start|begin|take off|launch)\b"),
]
SEARCH_KEYWORDS = [
    ("return_home", r"\b(return|come|go|fly|head)\b.*\bhome\b|\babort\b|\bland\b"),
    ("go_back_to_last_alert", r"\bgo back\b|\blook again\b|\bagain\b|\brevisit\b|\blast alert\b"),
    ("start_search", r"\b(start|begin|take off|launch)\b"),
    ("describe", r"\b(missing|lost|looking for|wearing|carrying|had)\b"),
]


def keyword_route(text: str, kind: str = "corridor") -> dict | None:
    import re
    t = text.lower()
    for name, pat in (SEARCH_KEYWORDS if kind == "search" else KEYWORDS):
        if re.search(pat, t):
            if name == "change_target":
                ph = re.search(r"\b(near|middle|centre|center|far)\b", t).group(1)
                return {"name": name, "phase": {"centre": "middle", "center": "middle"}.get(ph, ph)}
            return {"name": name}
    return None


def route_questions(kind: str = "corridor") -> dict:
    if kind == "search":
        return {"action": {"type": "choice", "instructions": "Which drone command did the operator ask for?",
                           "criteria": SEARCH_COMMANDS}}
    return {
        "action": {"type": "choice", "instructions": "Which drone command did the operator ask for?",
                    "criteria": COMMANDS},
        "phase": {"type": "choice", "instructions": "If the operator named a wire or phase to inspect, which one? "
                  "If none was named, pick the near phase.", "criteria": PHASES},
    }


def route(text: str, context: str = "", url: str = clef.URL, kind: str = "corridor") -> dict:
    """Clef-Flash routes a transcript to {name, phase?} with its probabilities; ok=False when unsure or failed."""
    what = ("a search-and-rescue drone looking for a missing person's belongings" if kind == "search"
            else "a power-line inspection drone")
    state = (f"You route spoken commands for {what}. The operator said: \"{text}\"\n"
             + (f"Mission state: {context}" if context else ""))
    d = clef.ask([], state, route_questions(kind), timeout=10.0, url=url)
    out = {"text": text, "ok": d.ok, "ms": d.latency_ms, "probs": d.probs, "error": d.error, "source": "CLEF"}
    if not d.ok:
        kw = keyword_route(text, kind)
        out.update(source="FALLBACK", error=f"Clef failed ({d.error[:60]}); keyword policy "
                   + (f"matched {kw['name']}" if kw else "matched nothing"))
        if kw:
            out.update(ok=True, name=kw["name"], command=kw)
        return out
    name, p = d.action, d.probs.get(d.action, 0.0)
    out.update(name=name, p=round(p, 3))
    if name == "none" or p < ROUTE_MIN_P:
        out["ok"] = False
        out["error"] = "not a drone command" if name == "none" else f"unsure ({name} {p:.2f} < {ROUTE_MIN_P})"
        return out
    out["command"] = {"name": name, "phase": d.extra.get("phase", "near")} if name == "change_target" else \
        {"name": name}
    return out


class VoiceWorker:
    """The speech models in one long-lived process; requests are serialised. close() stops it."""

    def __init__(self, timeout: float = 120.0):
        self.p = subprocess.Popen([str(LV_PY), "-I", str(ROOT / "patrol" / "voice_worker.py")], cwd=ROOT,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        self.lock = threading.Lock()
        self.ready = self._read(timeout)
        if not self.ready.get("ready"):
            raise RuntimeError(f"voice worker did not start: {self.ready}")

    def _read(self, timeout: float) -> dict:
        q: queue.Queue = queue.Queue()

        def reader():
            for line in self.p.stdout:
                if line.startswith("PATROL_VOICE "):
                    q.put(json.loads(line[len("PATROL_VOICE "):])); return
            q.put({"ok": False, "error": "voice worker exited"})
        threading.Thread(target=reader, daemon=True).start()
        try:
            return q.get(timeout=timeout)
        except queue.Empty:
            return {"ok": False, "error": f"no reply in {timeout} s"}

    def _call(self, req: dict, timeout: float = 60.0) -> dict:
        with self.lock:
            if self.p.poll() is not None:
                return {"ok": False, "error": "voice worker is not running"}
            self.p.stdin.write(json.dumps(req) + "\n"); self.p.stdin.flush()
            return self._read(timeout)

    def stt(self, wav: str | Path) -> dict:
        return self._call({"op": "stt", "wav": str(Path(wav).resolve())})

    def tts(self, text: str, out: str | Path) -> dict:
        return self._call({"op": "tts", "text": text, "out": str(Path(out).resolve())})

    def close(self):
        if self.p.poll() is None:
            try:
                self.p.stdin.close(); self.p.wait(timeout=10)
            except Exception:
                self.p.kill()


def note_text(ev: dict) -> str:
    n = ev.get("note") or {}
    if n.get("error"):
        return f"Flag {ev['id']}: the note could not be written."
    return f"Flag {ev['id']}, {n.get('severity', 'unknown')} severity. {n.get('note', '')} {n.get('recommendation', '')}"


class Speaker:
    """A mission sink: reads each LLM note aloud (and the end-of-mission summary), saving the WAV beside the photos
    and publishing a "speech" event the console plays. Speech runs on its own thread, off the control path."""

    def __init__(self, worker: VoiceWorker, out: Path, publish=None):
        self.worker, self.out, self.publish = worker, Path(out), publish
        (self.out / "media" / "audio").mkdir(parents=True, exist_ok=True)
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.futures = []
        self.spoken: list[dict] = []

    def say(self, key: str, text: str, **extra):
        def job():
            rel = f"media/audio/{key}.wav"
            r = self.worker.tts(text, self.out / rel)
            ev = {"id": key, "text": text, "audio": rel if r.get("ok") else None, "tts_ms": r.get("tts_ms"),
                  "audio_s": r.get("audio_s"), "error": r.get("error"), **extra}
            self.spoken.append(ev)
            if self.publish:
                self.publish("speech", **ev)
            return ev
        self.futures.append(self.pool.submit(job))

    def __call__(self, ev: dict):
        t = ev["type"]
        if t == "start":
            self.search = ev.get("spec", {}).get("kind") == "search"
            self.think = bool((ev.get("config") or {}).get("thinker"))
            return
        if getattr(self, "search", False):
            return self._search(ev)
        if t == "note":
            self.say(f"note_{ev['id']}", note_text(ev), flag=ev["id"])
        elif t == "summary":
            s = ev
            nf, nn = len(s.get("flags", [])), s.get("notes_ok", 0)
            self.say("summary", f"Patrol complete. {s.get('distance_m', 0):.0f} metres flown, "
                     f"{nf} flag{'' if nf == 1 else 's'}, {nn} note{'' if nn == 1 else 's'} written. "
                     f"{len(s.get('defects_found', []))} of {s.get('defects', 0)} planted defects found. "
                     f"The language model saw {100 * (s.get('llm_frame_fraction') or 0):.1f} percent of decisions.")

    def _search(self, ev: dict):
        """Search: each alert is read aloud, as qwen38's radio note when the slow thinker is on board (the note
        follows the alert by a few seconds) and from the alert itself when it is not or the note failed."""
        t = ev["type"]
        if t == "alert":
            self.alerts = getattr(self, "alerts", {}) | {ev["id"]: ev}
            if not self.think:
                self.say(f"alert_{ev['id']}", alert_text(ev), alert=ev["id"])
        elif t == "note":
            a = getattr(self, "alerts", {}).get(ev["id"])
            text = alert_text(a) if ev.get("error") and a else \
                f"Alert {ev['id']}. {ev.get('alert', '')} {ev.get('check', '')}".strip()
            self.say(f"note_{ev['id']}", text, alert=ev["id"])
        elif t == "summary":
            al = ev.get("alerts", [])
            fams = ", ".join(f"{a['family']} ({a['id']})" for a in al)
            self.say("summary", f"Search complete. {100 * (ev.get('coverage') or 0):.0f} percent of the area "
                     f"searched, {len(al)} alert{'' if len(al) == 1 else 's'}{': ' + fams if al else ''}. "
                     f"Battery used {ev.get('battery_used_pct', 0):.0f} percent.")

    def drain(self, timeout: float = 120.0):
        t0 = time.time()
        for f in list(self.futures):
            f.result(timeout=max(1.0, timeout - (time.time() - t0)))


def alert_text(a: dict) -> str:
    """An alert read out from the alert event alone (no qwen38 note)."""
    e, n = a["g"]
    return (f"Alert {a['id']}. Possible {a['family']}, {abs(e):.0f} metres {'east' if e >= 0 else 'west'} and "
            f"{abs(n):.0f} metres {'north' if n >= 0 else 'south'} of the search-area centre.")


def clue_options_text(d: dict) -> str:
    cl = d.get("clues") or []
    if not cl:
        return "I could not turn that into anything to look for. Please say it again."
    return "Looking for " + "; ".join(c["words"] for c in cl) + "."


def handle_utterance(wav: str | Path, worker: VoiceWorker, mission, speaker: Speaker | None = None,
                     url: str = clef.URL, on_start=None, on_describe=None) -> dict:
    """Speech in -> transcript -> Clef route -> command (or a spoken answer). Emits one "voice" event with the
    transcript, the route and its probabilities; the command itself lands at the mission's next tick. A search
    mission (one with .alerts) gets the search command set; a description goes to qwen38 for clue options."""
    heard = worker.stt(wav)
    if not heard.get("ok"):
        return mission.emit("voice", text=None, error=heard.get("error"), accepted=False)
    if sum(ch.isalnum() for ch in heard.get("text") or "") < 2:
        # silence or a tap: Clef routed an empty transcript to start_search at p 0.95 (patrol-79, 17:36), which would
        # nothing heard is never a command
        if speaker:
            speaker.say(f"voice_{mission.ticks}", "I did not hear anything.")
        return mission.emit("voice", text=heard.get("text"), error="nothing heard", accepted=False)
    kind = "search" if hasattr(mission, "alerts") else "corridor"
    r = route(heard["text"], mission.status_text(), url, kind=kind)
    cmd = r.get("command")
    ev = mission.emit("voice", text=heard["text"], stt_ms=heard.get("stt_ms"), route_ms=r.get("ms"),
                      route=r.get("name"), p=r.get("p"), probs=r.get("probs"), source=r.get("source"), command=cmd,
                      accepted=bool(cmd), error=r.get("error") or None)
    if not cmd:
        if speaker:
            speaker.say(f"voice_{mission.ticks}", "Sorry, I did not catch a command." if r.get("source") == "CLEF"
                        else "I heard you, but the command router is not answering.")
        return ev
    if cmd["name"] == "question":
        from .escalate import answer_question
        a = answer_question(heard["text"], mission.status_text())
        mission.emit("answer", question=heard["text"], **a)
        if speaker and a.get("text"):
            speaker.say(f"answer_{mission.ticks}", a["text"])
    elif cmd["name"] in ("start_mission", "start_search"):
        if on_start:
            on_start()
    elif cmd["name"] == "describe":
        from .thinker import describe
        d = describe(heard["text"])
        mission.emit("clue_options", text=heard["text"], clues=d.get("clues", []), error=d.get("error"),
                     wall_s=d.get("wall_s"), cached=d.get("cached", False))
        spoken = on_describe(d) if on_describe else False      # True: the callback rebuilt the mission and spoke
        if speaker and not spoken:
            speaker.say(f"clues_{mission.ticks}", clue_options_text(d))
    else:
        # acknowledge what the mission did, not what was asked: it applies the command at its next tick and may
        # refuse it (no alert yet, already returning), so wait for its decision (this runs off the control path)
        decided, out = threading.Event(), {}

        def reply(ok: bool, why: str):
            out.update(ok=ok, why=why)
            decided.set()
        mission.command(dict(cmd, _reply=reply))
        decided.wait(timeout=10.0)
        if speaker:
            ack = {"return_home": "Returning home",
                   "revisit_last_flag": "Going back to the last flag",
                   "go_back_to_last_alert": "Going back to the last alert",
                   "change_target": f"Inspecting the {cmd.get('phase', 'near')} phase"}.get(cmd["name"], "Okay")
            if not out:
                text = "The drone has not taken the command."
            elif out["ok"]:
                text = f"{ack} {out['why']}." if out["why"] else f"{ack}."
            else:
                text = f"I can't do that now: {out['why']}."
            speaker.say(f"ack_{mission.ticks}", text)
    return ev


class VoiceScript:
    """A mission hook that plays recorded commands as if spoken: {"tick:80": wav, "flag:1": wav, "alert:1": wav}. A
    "flag:K" ("alert:K") entry fires at the first tick after the K-th flag (search alert). Each utterance is handled
    on its own thread (off the control path)."""

    def __init__(self, entries: dict, worker: VoiceWorker, speaker: Speaker | None = None, url: str = clef.URL):
        self.pending = dict(entries)
        self.worker, self.speaker, self.url = worker, speaker, url
        self.threads: list[threading.Thread] = []

    def __call__(self, m):
        for key in list(self.pending):
            kind, n = key.split(":")
            if (kind == "tick" and m.ticks >= int(n)) or (kind == "flag" and len(m.sm.flags) >= int(n)) or \
                    (kind == "alert" and len(getattr(m, "alerts", ())) >= int(n)):
                wav = self.pending.pop(key)
                t = threading.Thread(target=handle_utterance, args=(ROOT / wav, self.worker, m, self.speaker,
                                                                    self.url), daemon=True)
                t.start(); self.threads.append(t)

    def join(self, timeout: float = 300.0):
        for t in self.threads:
            t.join(timeout)
