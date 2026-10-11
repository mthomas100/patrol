"""Escalation tier: qwen38 (vision) writes the inspection note for each flagged photo, off the control path.

Only flagged frames reach the LLM (the cost story). Calls go to llama-swap through the hold gate on :8090 with model
id `qwen38` and nothing else (GPU.md). While another agent holds the GPU the gate answers 503 "held"; the worker
waits and retries, so notes may arrive after the drone has moved on; the mission drains them at the end.
"""
from __future__ import annotations

import base64
import json
import re
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

URL = "http://127.0.0.1:8090/v1/chat/completions"
MODEL = "qwen38"          # the only llama-swap model this project may ever request

SYSTEM = ("You are a power-line inspection engineer writing notes from drone photos. Look at the photo yourself; "
          "the on-board model's guess may be wrong. Reply with one JSON object only, no prose around it.")

PROMPT = """Zoomed drone photo(s) from a simulated transmission-line inspection, taken at {x:.0f} m along a {length:.0f} m corridor,
aimed at the {what}. The on-board decision model flagged possible damage; its probabilities: {nouls}.
Write the inspection note as JSON with exactly these keys:
  "defect_type": one of "broken_insulator", "frayed_conductor", "vegetation", "foreign_object", "none",
  "component": the part affected, in a few words,
  "severity": one of "low", "medium", "high", "critical",
  "note": one or two sentences saying what is visible in the photo,
  "recommendation": one sentence for the maintenance crew.
If nothing is wrong in the photo, use "none" and say so."""


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


def write_note(jpeg, x: float, what: str, nouls: dict, length: float = 300.0,
               max_wait_s: float = 900.0, timeout: float = 240.0) -> dict:
    """One qwen38 vision call; waits out GPU holds (503) up to max_wait_s. Returns the note plus timing."""
    req = {"model": MODEL, "max_tokens": 500, "temperature": 0.2, "thinking": {"type": "disabled"},
           "messages": [{"role": "system", "content": SYSTEM},
                        {"role": "user", "content": [
                            {"type": "text", "text": PROMPT.format(x=x, length=length, what=what,
                                                                   nouls=json.dumps({k: round(v, 2) for k, v in
                                                                                     nouls.items()}))},
                            *[{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,"
                                                                        + base64.b64encode(j).decode()}}
                              for j in (jpeg if isinstance(jpeg, (list, tuple)) else [jpeg])]]}]}
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
                usage=body.get("usage"))
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
            note = write_note(jpeg, flag.target.x, what, flag.nouls, self.length)
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
