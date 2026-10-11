"""Escalation tier: qwen38 (vision) writes the inspection note for each flagged photo, off the control path.

Only flagged frames reach the LLM (the cost story). Calls go to llama-swap through the hold gate on :8090 with model
id `qwen38` and nothing else (GPU.md). While another agent holds the GPU the gate answers 503 "held"; the worker
waits and retries, so notes may arrive after the drone has moved on; the mission drains them at the end.
"""
from __future__ import annotations

import base64
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# PATROL_LLM_BASE points the qwen38 calls at another OpenAI-style server or a proxy (HOSTED.md)
URL = os.environ.get("PATROL_LLM_BASE", "http://127.0.0.1:8090").rstrip("/") + "/v1/chat/completions"
REFERENCE = Path(__file__).resolve().parents[1] / "fixtures" / "reference"
MODEL = "qwen38"          # the only llama-swap model this project may ever request

SYSTEM = ("You are a power-line inspection engineer writing notes from drone photos. Look at the photo yourself; "
          "the on-board model's guess may be wrong. Reply with one JSON object only, no prose around it.")

PROMPT = """Zoomed drone photo(s) from a simulated transmission-line inspection, taken at {x:.0f} m along a {length:.0f} m corridor,
aimed at the {what}. The on-board decision model flagged possible damage; its probabilities: {nouls}.
{lidar}
Write the inspection note as JSON with exactly these keys:
  "defect_type": one of "broken_insulator", "frayed_conductor", "vegetation", "foreign_object", "none", where
     broken_insulator = the insulator string itself is damaged: discs missing (gaps in the stack), cracked, blackened
       or scorched, or a disc knocked loose and hanging askew; fragments of discs below it;
     frayed_conductor = the wire itself has broken strands splayed out or a burnt patch;
     vegetation = a tree within about a metre of a wire;
     foreign_object = something that is not part of the line equipment (bird nest, sticks, plastic sheet, kite),
  "component": the part affected, in a few words,
  "severity": one of "low", "medium", "high", "critical",
  "note": one or two sentences saying what is visible in the photo,
  "recommendation": one sentence for the maintenance crew.
If nothing is wrong in the photo, use "none" and say so.{reference}"""

REFERENCE_TEXT = ("\nThe LAST image is not from this inspection: it is a catalogue reference photo of a healthy {what} of "
                  "the same design, for comparison. Compare the inspection photo(s) against it (count and spacing of the "
                  "glass discs, the wire's outline) before naming the defect.")


def reference_for(what: str) -> tuple[str, bytes] | None:
    """A catalogue photo of the healthy component of the same design (rendered from a defect-free scene, the way an
    inspector's reference library would hold one); None when no reference fits."""
    for key, name, label in (("insulator", "insulator_healthy.jpg", "insulator string (nine evenly spaced discs)"),
                             ("conductor", "conductor_healthy.jpg", "conductor span")):
        if key in what and (REFERENCE / name).exists():
            return label, (REFERENCE / name).read_bytes()
    return None


def _post(req: dict, timeout: float) -> dict:
    r = urllib.request.urlopen(urllib.request.Request(URL, json.dumps(req).encode(),
                                                      {"Content-Type": "application/json"}), timeout=timeout)
    return json.loads(r.read())


def parse_note(text: str) -> dict:
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        return {"defect_type": "unknown", "note": text[:300], "parse_error": True}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"defect_type": "unknown", "note": text[:300], "parse_error": True}


def write_note(jpeg, x: float, what: str, nouls: dict, length: float = 300.0, clearance=None,
               max_wait_s: float = 900.0, timeout: float = 240.0, reference: bool = True) -> dict:
    """One qwen38 vision call; waits out GPU holds (503) up to max_wait_s. Returns the note plus timing."""
    lidar = ("Rangefinder (lidar): no trees in view." if clearance is None else
             f"Rangefinder (lidar): nearest tree surface {clearance:.1f} m from the nearest conductor (a tree is a "
             "hazard only within about 1 m; one that merely looks close in the photo may be far behind the line).")
    imgs = list(jpeg if isinstance(jpeg, (list, tuple)) else [jpeg])
    ref = reference_for(what) if reference else None
    if ref:
        imgs.append(ref[1])
    req = {"model": MODEL, "max_tokens": 500, "temperature": 0.2, "thinking": {"type": "disabled"},
           "messages": [{"role": "system", "content": SYSTEM},
                        {"role": "user", "content": [
                            {"type": "text", "text": PROMPT.format(x=x, length=length, what=what, lidar=lidar,
                                                                   reference=REFERENCE_TEXT.format(what=ref[0]) if ref
                                                                   else "",
                                                                   nouls=json.dumps({k: round(v, 2) for k, v in
                                                                                     nouls.items()}))},
                            *[{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,"
                                                                        + base64.b64encode(j).decode()}}
                              for j in imgs]]}]}
    t0 = time.time()
    waited, attempts = 0.0, 0
    while True:
        attempts += 1
        t1 = time.time()
        try:
            body = _post(req, timeout)
            break
        except urllib.error.HTTPError as e:
            if e.code == 503 and time.time() - t0 < max_wait_s:
                time.sleep(10); waited += time.time() - t1
                continue
            return {"error": f"HTTP {e.code}: {e.read()[:200].decode(errors='replace')}",
                    "wall_s": round(time.time() - t0, 1), "attempts": attempts}
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            return {"error": f"{type(e).__name__}: {e}"[:200], "wall_s": round(time.time() - t0, 1),
                    "attempts": attempts}
    msg = body["choices"][0]["message"]
    note = parse_note(msg.get("content") or "")
    note.update(model=MODEL, wall_s=round(time.time() - t0, 1), held_wait_s=round(waited, 1), attempts=attempts,
                usage=body.get("usage"), reference=ref[0] if ref else None)
    return note


class Escalator:
    """Background worker: submit(flag, jpeg, on_note) returns at once; drain() waits for outstanding notes."""

    def __init__(self, length: float = 300.0, workers: int = 1):
        self.length = length
        self.pool = ThreadPoolExecutor(max_workers=workers)
        self.futures = []
        self.lock = threading.Lock()
        self.calls = 0

    def submit(self, flag, jpeg: bytes, on_note):
        what = flag.target.why or "nearest line equipment"

        def job():
            note = write_note(jpeg, flag.target.x, what, flag.nouls, self.length, clearance=flag.clearance)
            with self.lock:
                self.calls += 1
                flag.note = note
                on_note(flag, note)
            return note

        self.futures.append(self.pool.submit(job))

    def drain(self, timeout: float = 1200.0) -> int:
        t0 = time.time()
        for f in self.futures:
            f.result(timeout=max(1.0, timeout - (time.time() - t0)))
        return len(self.futures)


def answer_question(question: str, status: str, max_wait_s: float = 300.0) -> dict:
    """The operator asked something out loud: qwen38 answers in one or two spoken sentences from the mission state
    (no image). Waits out GPU holds like the notes do."""
    req = {"model": MODEL, "max_tokens": 120, "temperature": 0.2, "thinking": {"type": "disabled"},
           "messages": [{"role": "system", "content": "You are the voice of a power-line inspection drone talking to "
                         "its operator. Answer in at most two short spoken sentences, from the mission state only; "
                         "no lists, no markdown."},
                        {"role": "user", "content": f"Mission state: {status}\nOperator: {question}"}]}
    t0 = time.time()
    while True:
        try:
            body = _post(req, 120)
            text = re.sub(r"<think>.*?</think>", "", body["choices"][0]["message"].get("content") or "",
                          flags=re.S).strip()
            return {"text": text, "wall_s": round(time.time() - t0, 1), "model": MODEL}
        except urllib.error.HTTPError as e:
            if e.code == 503 and time.time() - t0 < max_wait_s:
                time.sleep(5); continue
            return {"error": f"HTTP {e.code}", "wall_s": round(time.time() - t0, 1)}
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            return {"error": f"{type(e).__name__}: {e}"[:200], "wall_s": round(time.time() - t0, 1)}
