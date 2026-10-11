"""Compare Clef-Flash question wordings on saved fixture frames: separation between defect and clean frames.

usage: .venv/bin/python -m tools.tune_schema FIXTURE_DIR [--variants A B ...] > runs/.../tune.log
For each variant and each signal (action probabilities, nouls) prints min over defect frames, max over clean
frames, and the gap (positive gap = a threshold separates them perfectly).
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from patrol import clef  # noqa: E402

SHORT_ACTIONS = {
    "continue": "everything in view looks normal; keep flying",
    "hover_and_photograph": "something might be wrong but it is unclear; stop and take a close-up photo",
    "go_back": "a possible problem was just passed; fly back to look again",
    "flag_damage": "damage is clearly visible; flag it",
}
NOULS = {
    "insulator_damaged": "Is any glass insulator string (the stack of discs hanging under the crossarm) missing "
                         "discs, with a gap in the stack, or with a disc tilted, cracked or blackened?",
    "conductor_frayed": "Does any conductor wire have broken strands sticking out or a blackened burnt patch?",
    "vegetation_close": "Is a tree crown touching a wire or within a metre of one?",
    "foreign_object": "Is a bird nest, sticks, a plastic sheet, a kite or other debris on a crossarm or a wire?",
}


def variants():
    full = clef.schema()
    return {
        "A_current": full,
        "B_component_nouls": {"action": {"type": "choice", "instructions": full["action"]["instructions"],
                                         "criteria": SHORT_ACTIONS},
                              **{k: {"type": "noul", "instructions": v} for k, v in NOULS.items()}},
        "C_action_only_short": {"action": {"type": "choice", "instructions": "Pick the drone's next action.",
                                           "criteria": SHORT_ACTIONS}},
        "D_nouls_first_then_action": {**{k: {"type": "noul", "instructions": v} for k, v in NOULS.items()},
                                      "action": full["action"]},
        "E_damage_only": {"damage": full["damage"]},
    }


def jpeg(path, w=512):
    im = Image.open(path); h = round(im.height * w / im.width)
    b = io.BytesIO(); im.resize((w, h), Image.LANCZOS).save(b, "JPEG", quality=85); return b.getvalue()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("fixture"); ap.add_argument("--variants", nargs="*")
    ap.add_argument("--minimal-state", action="store_true"); ap.add_argument("--width", type=int, default=512)
    a = ap.parse_args()
    d = Path(a.fixture)
    rows = [json.loads(l) for l in (d / "frames.jsonl").read_text().splitlines()]
    # positives: defect within 16 m in an inspect frame, or a zoom photo of it; negatives: everything clean
    pos = [r for r in rows if r["truth"] and (r["camera"] == "zoom" or min(t["depth"] for t in r["truth"]) <= 16)]
    neg = [r for r in rows if not r["truth"]]
    vs = variants()
    for name in a.variants or vs:
        q = vs[name]
        sig = {}
        for label, group in (("pos", pos), ("neg", neg)):
            for r in group:
                st = "Inspection drone camera frame." if a.minimal_state else clef.state_text(
                    r["tel"], {"camera": r["camera"], "hovering": r["camera"] == "zoom"})
                req_q = q
                body = _raw(jpeg(d / r["file"], a.width), st, req_q)
                for qid, ans in body.items():
                    if ans["type"] == "noul":
                        sig.setdefault(qid, {"pos": [], "neg": []})[label].append(ans["noul"])
                    elif ans["type"] == "choice":
                        for o, p in ans["probabilities"].items():
                            sig.setdefault(f"{qid}.{o}", {"pos": [], "neg": []})[label].append(p)
        print(f"== {name} (pos {len(pos)}, neg {len(neg)})")
        for k, v in sig.items():
            if not v["pos"] or not v["neg"]:
                continue
            gap = min(v["pos"]) - max(v["neg"])
            print(f"  {k:38s} pos min {min(v['pos']):.2f} mean {sum(v['pos'])/len(v['pos']):.2f}  "
                  f"neg max {max(v['neg']):.2f} mean {sum(v['neg'])/len(v['neg']):.2f}  gap {gap:+.2f}", flush=True)


def _raw(jpg, state, questions):
    import base64, urllib.request
    req = {"model": clef.MODEL, "state": state, "questions": questions,
           "images": ["data:image/jpeg;base64," + base64.b64encode(jpg).decode()]}
    r = urllib.request.urlopen(urllib.request.Request(clef.URL, json.dumps(req).encode(),
                                                      {"Content-Type": "application/json"}), timeout=60)
    return json.loads(r.read())["answers"]


if __name__ == "__main__":
    main()
