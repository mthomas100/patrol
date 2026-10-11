"""qwen38, the slow thinker on board (BRIEF "Two models on board"): a few calls per mission, never in the control loop.

Roles, each one function returning a dict (with "error" instead of raising when the model is unavailable):
- describe(text): the family's words -> clues {name, family, words, size_m} (what to look for from above), cached;
- alert_note(...): a radio alert and what the ground team should check, from the close-up and the sweep crop;
- trail_plan(...): after a find, which unsearched sectors to search next and why (lost hikers follow trails and
  drainages and leave things along their route); code validates the answer before the planner uses it;
- second_opinion(...): a close call at the lowest investigate step, judged from the same photos.

Every call goes through the hold gate on :8090 with model id qwen38 only (GPU.md), waits out GPU holds (HTTP 503),
and is counted by role in CALLS so reports can show the LLM share and Clef latency with qwen38 idle vs active.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

URL = "http://127.0.0.1:8090/v1/chat/completions"
MODEL = "qwen38"          # the only llama-swap model this project may ever request
CACHE = Path(__file__).resolve().parents[1] / "fixtures" / "clues"
CALLS: Counter = Counter()
ACTIVE = threading.Event()      # set while a qwen38 call is in flight (Clef latency is split on it)
_lock = threading.Lock()
_active_n = [0]


def _img(j: bytes) -> dict:
    return {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(j).decode()}}


def chat(role: str, system: str, text: str, images=(), max_tokens: int = 400, timeout: float = 120.0,
         max_wait_s: float = 600.0) -> dict:
    """One qwen38 call; returns {"text", "wall_s", "held_wait_s"} or {"error", ...}."""
    req = {"model": MODEL, "max_tokens": max_tokens, "temperature": 0.2, "thinking": {"type": "disabled"},
           "messages": [{"role": "system", "content": system},
                        {"role": "user", "content": [{"type": "text", "text": text}, *[_img(j) for j in images]]}]}
    t0, waited = time.time(), 0.0
    with _lock:
        _active_n[0] += 1; ACTIVE.set()
    try:
        while True:
            t1 = time.time()
            try:
                r = urllib.request.urlopen(urllib.request.Request(URL, json.dumps(req).encode(),
                                                                  {"Content-Type": "application/json"}), timeout=timeout)
                body = json.loads(r.read())
                break
            except urllib.error.HTTPError as e:
                if e.code == 503 and time.time() - t0 < max_wait_s:     # another agent holds the GPU: wait it out
                    time.sleep(5); waited += time.time() - t1
                    continue
                return {"error": f"HTTP {e.code}", "wall_s": round(time.time() - t0, 1)}
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                return {"error": f"{type(e).__name__}: {e}"[:160], "wall_s": round(time.time() - t0, 1)}
    finally:
        with _lock:
            _active_n[0] -= 1
            if not _active_n[0]:
                ACTIVE.clear()
    CALLS[role] += 1
    text = (body["choices"][0]["message"].get("content") or "")
    return {"text": re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip(), "wall_s": round(time.time() - t0, 1),
            "held_wait_s": round(waited, 1), "usage": body.get("usage")}


def _json(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text or "", flags=re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------- 1. the family's words -> clues
DESCRIBE_SYSTEM = ("You help a search-and-rescue drone team. You turn a family's description of a missing person's "
                   "belongings into clues that a drone camera looking down from the air can search for.")
DESCRIBE = """The family said: "{text}"

Write one clue for each separate thing they mention that could be lying on the ground and be seen from the air (a
bag, a tent, clothing, gear, a pet, a sign made of rocks). Skip the person themselves, names and ages.
Answer with JSON only, in this form:
{{"clues": [{{"name": "<colour>_<thing> in snake_case, for example blue_backpack",
  "family": "<the family's own short words for it>",
  "words": "<one sentence starting with 'a' or 'an': what it looks like from above lying on the ground: its colour, its shape, the parts you could see, and its rough size>",
  "size_m": <its largest dimension in metres, a number>}}]}}
Keep the colour the family gave."""


def describe(text: str, use_cache: bool = True) -> dict:
    key = hashlib.sha1(text.strip().lower().encode()).hexdigest()[:12]
    path = CACHE / f"{key}.json"
    if use_cache and path.exists():
        return json.loads(path.read_text()) | {"cached": True}
    r = chat("describe", DESCRIBE_SYSTEM, DESCRIBE.format(text=text.strip()), max_tokens=600)
    if "error" in r:
        return {"error": r["error"], "text": text}
    j = _json(r["text"]) or {}
    clues = []
    for c in j.get("clues", []):
        try:
            name = re.sub(r"[^a-z0-9_]", "", str(c["name"]).lower().replace(" ", "_"))[:40]
            clues.append({"name": name, "family": str(c["family"])[:60], "words": str(c["words"])[:300],
                          "size_m": float(min(max(float(c["size_m"]), 0.1), 10.0))})
        except (KeyError, TypeError, ValueError):
            continue
    out = {"text": text, "clues": clues, "wall_s": r["wall_s"], "model": MODEL}
    if clues:
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out, indent=1))
    return out


# ---------------------------------------------------------------- 2. alert note
NOTE_SYSTEM = ("You write short radio alerts for a search-and-rescue ground team from drone photos. Be factual and "
               "brief, and never claim more than the photos show.")
NOTE = """A search drone looking for a missing hiker's belongings has confirmed a possible clue.
Clue: {family}: {words}
Where: {where}
The drone's spotting model rated the close-up {conf:.0%} likely to be the {family}.
Photo 1: the zoom close-up from {h:.0f} m. Photo 2: the spot as first seen from {sweep_h:.0f} m.
Answer with JSON only:
{{"alert": "<one sentence for the radio, under 25 words: what was found and where>",
  "check": "<one sentence: what the ground team should check or do there>",
  "agree": <true if photo 1 looks like the {family}, else false>}}"""


def alert_note(clue: dict, where: str, conf: float, h: float, sweep_h: float, closeup: bytes,
               crop: bytes | None) -> dict:
    imgs = [closeup] + ([crop] if crop else [])
    r = chat("note", NOTE_SYSTEM, NOTE.format(family=clue["family"], words=clue["words"], where=where, conf=conf, h=h,
                                              sweep_h=sweep_h), imgs, max_tokens=250)
    if "error" in r:
        return r
    j = _json(r["text"]) or {"alert": r["text"][:200], "parse_error": True}
    return j | {"wall_s": r["wall_s"], "held_wait_s": r["held_wait_s"]}


# ---------------------------------------------------------------- 3. trail reasoning
TRAIL_SYSTEM = ("You are the search planner for a search-and-rescue team, deciding where the drone searches next. "
                "Lost hikers usually stay on or near trails and other linear features such as streams, tend to "
                "continue in the direction they were going, and leave belongings along their route.")
TRAIL = """The search area is {area}. x is metres east, y is metres north.
Map: the trailhead (last known point) is at {lkp}. The hiking trail passes through {trail}. A stream passes through {stream}.
Finds so far, in order: {finds}.
The area is divided into sectors; these are not searched yet:
{sectors}
Which sectors should the drone search next? Answer with JSON only:
{{"first": [<up to {k} sector ids, most promising first>], "reason": "<one sentence for the operator, under 30 words>"}}"""


def _pts(pts, every: int = 5) -> str:
    return ", ".join(f"({x:.0f}, {y:.0f})" for x, y in pts[::every] + ([pts[-1]] if len(pts) % every != 1 else []))


def trail_plan(area, feats: dict, finds: list[dict], sectors: list[dict], k: int = 6) -> dict:
    sec = "\n".join(f"- {s['id']}: x {min(s['x0'], s['x1']):.0f} to {max(s['x0'], s['x1']):.0f}, y {s['y'] - s['h'] / 2:.0f} "
                    f"to {s['y'] + s['h'] / 2:.0f}" for s in sectors)
    fd = "; ".join(f"{f['family']} at ({f['g'][0]:.0f}, {f['g'][1]:.0f}) after {f['t']:.0f} s" for f in finds) or "none"
    xs, ys = [p[0] for p in area], [p[1] for p in area]
    text = TRAIL.format(area=f"x {min(xs):.0f} to {max(xs):.0f}, y {min(ys):.0f} to {max(ys):.0f}",
                        lkp=f"({feats['lkp'][0]:.0f}, {feats['lkp'][1]:.0f})", trail=_pts(feats["trail"]),
                        stream=_pts(feats["stream"]), finds=fd, sectors=sec, k=k)
    r = chat("trail", TRAIL_SYSTEM, text, max_tokens=300)
    if "error" in r:
        return r
    j = _json(r["text"]) or {}
    ids = {s["id"] for s in sectors}
    first = [x for x in j.get("first", []) if isinstance(x, str) and x in ids]
    first = list(dict.fromkeys(first))[:k]                          # code validates: known, unsearched, no repeats
    return {"first": first, "reason": str(j.get("reason", ""))[:240], "raw_ok": bool(j), "wall_s": r["wall_s"],
            "held_wait_s": r["held_wait_s"]}


# ---------------------------------------------------------------- 4. second opinion on a close call
SECOND_SYSTEM = ("You check drone photos for a search-and-rescue team. Answer only from what the photos show; a "
                 "wrong alert sends a ground team on a long walk, a missed clue can cost a life.")
SECOND = """The drone's fast spotting model is unsure whether this is the missing person's {family} ({words}).
Photo 1: the zoom close-up from {h:.0f} m. Photo 2: the same spot from {sweep_h:.0f} m.
Answer with JSON only: {{"is_clue": <true or false>, "confidence": <0 to 1>, "why": "<under 20 words>"}}"""


def second_opinion(clue: dict, h: float, sweep_h: float, closeup: bytes, crop: bytes | None) -> dict:
    r = chat("second_opinion", SECOND_SYSTEM, SECOND.format(family=clue["family"], words=clue["words"], h=h,
                                                             sweep_h=sweep_h),
             [closeup] + ([crop] if crop else []), max_tokens=120, max_wait_s=120)
    if "error" in r:
        return r
    j = _json(r["text"]) or {}
    try:
        return {"is_clue": bool(j["is_clue"]), "confidence": float(j.get("confidence", 0.5)),
                "why": str(j.get("why", ""))[:160], "wall_s": r["wall_s"]}
    except (KeyError, TypeError, ValueError):
        return {"error": f"unparsed: {r['text'][:120]}", "wall_s": r["wall_s"]}


class Worker:
    """Runs thinker jobs off the control loop: submit(fn, *args, on_done=cb) returns at once."""

    def __init__(self):
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.futures = []

    def submit(self, fn, *args, on_done=None, **kw):
        def job():
            out = fn(*args, **kw)
            if on_done:
                on_done(out)
            return out
        self.futures.append(self.pool.submit(job))

    def busy(self) -> bool:
        return any(not f.done() for f in self.futures)

    def drain(self, timeout: float = 600.0):
        t0 = time.time()
        for f in self.futures:
            try:
                f.result(timeout=max(1.0, timeout - (time.time() - t0)))
            except Exception:
                pass
