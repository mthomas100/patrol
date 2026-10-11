"""S3 trail-reasoning A/B: the same path-seed flights with qwen38's sector reordering on and off.

The brief's test for trail reasoning is the time to the second find with reordering vs without, on seeds whose clue
items lie along the trail (`--on-trail`). The first find happens before any plan exists, so its time differs between
the two arms only through realtime noise; the gap from the first find to each later find is the cleaner measure.
Tuning items only (backpack, tent, jacket; tarp decoy). Writes OUT/SUMMARY.md and OUT/summary.json.

usage: .venv/bin/python -m tools.trail_ab --seeds 5 6 [--terrain grass] [--lockstep] [--out runs/s3-trail-ab]
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ITEMS = "blue_backpack,orange_tent,red_jacket,blue_tarp"
CLUES = "blue_backpack,orange_tent,red_jacket"


def fly(d: Path, seed: int, terrain: str, trail: bool, lockstep: bool) -> dict:
    cmd = [sys.executable, "-m", "patrol.cli", "search", "--think", "--on-trail", "--terrain", terrain, "--seed",
           str(seed), "--items", ITEMS, "--clues", CLUES, "--out", str(d)] + ([] if trail else ["--no-trail"]) \
        + (["--lockstep"] if lockstep else [])
    d.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with open(d / "stdout.log", "w") as f:
        rc = subprocess.run(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT).returncode
    s = json.loads((d / "summary.json").read_text()) if (d / "summary.json").exists() else {}
    sc = json.loads((d / "score.json").read_text()) if (d / "score.json").exists() else {}
    clue_alerts = sorted(a["t"] for a in s.get("alerts", []) if a["clue"] in CLUES.split(","))
    t = clue_alerts + [None] * (3 - len(clue_alerts))
    return {"seed": seed, "trail": trail, "lockstep": lockstep, "rc": rc, "run": str(d.relative_to(ROOT)),
            "recall": sc.get("recall"), "false_alerts": len(sc.get("false_alerts", [])), "t_finds": t,
            "gap12": round(t[1] - t[0], 1) if t[1] is not None else None,
            "gap13": round(t[2] - t[0], 1) if t[2] is not None else None,
            "sim_s": s.get("sim_s"), "wall_s": round(time.time() - t0, 1), "battery_pct": s.get("battery_used_pct"),
            "llm": s.get("llm_by_role"), "plans_applied": sum(1 for p in s.get("plans", []) if p.get("first")),
            "clef_idle": [s.get("clef_qwen_idle", {}).get(k) for k in ("n", "median_ms", "p90_ms")],
            "clef_active": [s.get("clef_qwen_active", {}).get(k) for k in ("n", "median_ms", "p90_ms")]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[5, 6])
    ap.add_argument("--terrain", default="grass")
    ap.add_argument("--lockstep", action="store_true", help="pause the world while Clef thinks (less timing noise)")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    out = Path(a.out or ROOT / "runs" / time.strftime("s3-trail-ab-%H%M%S"))
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for seed in a.seeds:
        for trail in (True, False):
            r = fly(out / f"{a.terrain}{seed}-{'trail' if trail else 'notrail'}", seed, a.terrain, trail, a.lockstep)
            rows.append(r)
            print(json.dumps(r), flush=True)
    (out / "summary.json").write_text(json.dumps(rows, indent=1))
    L = [f"# Trail reasoning A/B ({a.terrain}, seeds {a.seeds}, {'lockstep' if a.lockstep else 'realtime'})", "",
         "Same flight with qwen38 reordering sectors after each find (trail) and without (notrail). Times are sim "
         "seconds; gap = time from the first find to the second (third) find.", "",
         "| seed | arm | recall | false | finds s | gap 1-2 | gap 1-3 | mission sim s | battery % | plans applied | "
         "qwen38 calls | Clef idle n/p50/p90 | Clef while qwen38 busy n/p50/p90 | run |", "|" + "---|" * 14]
    for r in rows:
        L.append(f"| {r['seed']} | {'trail' if r['trail'] else 'notrail'} | {r['recall']} | {r['false_alerts']} | "
                 f"{r['t_finds']} | {r['gap12']} | {r['gap13']} | {r['sim_s']} | {r['battery_pct']} | "
                 f"{r['plans_applied']} | {r['llm']} | {r['clef_idle']} | {r['clef_active']} | `{r['run']}` |")
    pairs = [(x, y) for x in rows for y in rows if x["seed"] == y["seed"] and x["trail"] and not y["trail"]]
    d12 = [y["gap12"] - x["gap12"] for x, y in pairs if x["gap12"] is not None and y["gap12"] is not None]
    d13 = [y["gap13"] - x["gap13"] for x, y in pairs if x["gap13"] is not None and y["gap13"] is not None]
    if d12:
        L += ["", f"Reordering saved {statistics.mean(d12):.1f} s on average from the first to the second find "
                  f"(per seed {[round(v, 1) for v in d12]}) and {statistics.mean(d13):.1f} s to the third "
                  f"(per seed {[round(v, 1) for v in d13]}). Positive = faster with reordering."]
    (out / "SUMMARY.md").write_text("\n".join(L) + "\n")
    print(f"summary: {out}/SUMMARY.md")


if __name__ == "__main__":
    main()
