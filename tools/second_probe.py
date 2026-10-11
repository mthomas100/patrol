"""S3 second-opinion probe: how well does qwen38 tell a clue from a decoy on the drone's own close-ups?

Replays the zoom close-ups saved by finished tuning flights (every confirm photo), asks thinker.second_opinion() about
the clue Clef leaned to, and scores the answer against ground truth (the scene's planted items, read here for
scoring only). Tuning runs only. Writes OUT/probe.jsonl and OUT/SUMMARY.md.

usage: .venv/bin/python -m tools.second_probe runs/s2-tune-snow2c runs/s2-tune-grass3c ... [--out runs/s3-second-probe]
"""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

from patrol import clues as cluelib, thinker

ROOT = Path(__file__).resolve().parents[1]
MATCH_R = 5.0


def spots(run: Path):
    """(spot, confirm events) per investigated spot, with the truth: the planted item within MATCH_R, else nothing."""
    items = json.loads((run / "scene.json").read_text())["items"]
    inv, conf = {}, {}
    for line in (run / "mission.jsonl").open():
        e = json.loads(line)
        if e["type"] == "investigate":
            inv[e["spot"]["id"]] = e["spot"]
        elif e["type"] == "confirm" and e.get("ok"):
            conf.setdefault(e["id"], []).append(e)
    for sid, s in inv.items():
        near = min(items, key=lambda it: math.dist((it["x"], it["y"]), s["g"]), default=None)
        truth = near if near and math.dist((near["x"], near["y"]), s["g"]) <= MATCH_R else None
        yield s, conf.get(sid, []), truth


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--out", default=str(ROOT / "runs" / "s3-second-probe"))
    ap.add_argument("--min-conf", type=float, default=0.6)
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rows = []
    with open(out / "probe.jsonl", "w") as f:
        for run in map(Path, a.runs):
            names = [c["name"] for c in json.loads((run / "mission.jsonl").open().readline())["clues"]]
            cl = {c["name"]: c for c in cluelib.clues(names)}
            for s, confs, truth in spots(run):
                for e in confs:
                    clue = e["clue"] if e.get("clue") in cl else max(e["nouls"], key=e["nouls"].get)
                    jpg = (run / e["photo"]).read_bytes()
                    crop = (run / s["crop"]).read_bytes() if s.get("crop") and (run / s["crop"]).exists() else None
                    t0 = time.time()
                    r = thinker.second_opinion(cl[clue], e["h"], s["sweep_h"], jpg, crop)
                    is_clue = bool(truth and truth["name"] == clue)
                    row = {"run": run.name, "spot": s["id"], "h": e["h"], "asked": clue, "truth": truth["name"] if
                           truth else "nothing", "truth_is_clue": is_clue, "clef_noul": e["noul"],
                           "clef_verdict": e["verdict"], "qwen": r, "wall_s": round(time.time() - t0, 1)}
                    rows.append(row); f.write(json.dumps(row) + "\n"); f.flush()
                    print(json.dumps({k: row[k] for k in ("run", "spot", "h", "asked", "truth", "clef_noul")}
                                     | {"is_clue": r.get("is_clue"), "conf": r.get("confidence"),
                                        "err": r.get("error")}), flush=True)
    ok = [r for r in rows if "error" not in r["qwen"]]
    yes = lambda r: r["qwen"]["is_clue"] and r["qwen"]["confidence"] >= a.min_conf
    pos, neg = [r for r in ok if r["truth_is_clue"]], [r for r in ok if not r["truth_is_clue"]]
    L = ["# qwen38 second-opinion probe (tuning close-ups)", "",
         f"Runs: {', '.join(a.runs)}. Each confirm close-up replayed to `thinker.second_opinion` for the clue Clef "
         f"leaned to; truth = planted item within {MATCH_R:.0f} m (scoring only). Confirm = is_clue and confidence "
         f">= {a.min_conf}.", "",
         f"- asked {len(rows)}, answered {len(ok)}, errors {len(rows) - len(ok)}",
         f"- true clue close-ups confirmed: {sum(map(yes, pos))}/{len(pos)}",
         f"- decoy or nothing close-ups confirmed (would be false alerts): {sum(map(yes, neg))}/{len(neg)}",
         f"- qwen38 wall per call: median {sorted(r['wall_s'] for r in rows)[len(rows) // 2] if rows else None} s", "",
         "| run | spot | h | asked | truth | Clef noul | Clef verdict | qwen38 is_clue | conf | why |", "|" + "---|" * 10]
    for r in rows:
        q = r["qwen"]
        L.append(f"| {r['run']} | {r['spot']} | {r['h']:.0f} | {r['asked']} | {r['truth']} | {r['clef_noul']} | "
                 f"{r['clef_verdict']} | {q.get('is_clue', q.get('error'))} | {q.get('confidence')} | "
                 f"{str(q.get('why', '')).replace('|', '/')} |")
    (out / "SUMMARY.md").write_text("\n".join(L) + "\n")
    print(f"summary: {out}/SUMMARY.md")


if __name__ == "__main__":
    main()
