"""Tuning aid (scoring side, reads ground truth after the flight): Clef's sweep and confirm answers grouped by what
was really at the spot, so gate thresholds are set from numbers. Use on tuning items only (DECISIONS testing doctrine).

usage: .venv/bin/python -m tools.gate_probe runs/<search run> [more runs]
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path


def label(g, items, r=3.0):
    near = [(math.dist(g, (it["x"], it["y"])), it["name"]) for it in items]
    d, n = min(near, default=(1e9, None))
    return n if d <= max(r, 0.6 * next(it["size_m"] for it in items if it["name"] == n)) else "background"


def q(v):
    v = sorted(v)
    return f"n={len(v)} min={v[0]:.3f} p50={v[len(v) // 2]:.3f} p90={v[int(0.9 * (len(v) - 1))]:.3f} max={v[-1]:.3f}" \
        if v else "n=0"


def main(argv=None):
    runs = [Path(a) for a in (argv or sys.argv[1:])]
    sweep, conf = defaultdict(lambda: defaultdict(list)), defaultdict(list)
    for run in runs:
        items = json.loads((run / "scene.json").read_text())["items"]
        evs = [json.loads(l) for l in (run / "mission.jsonl").read_text().splitlines()]
        spots = {}
        for e in evs:
            if e["type"] == "frame":
                for c in e["candidates"]:
                    if c.get("status") == "judged" and c.get("nouls") is not None and c["g"]:
                        lb = label(c["g"], items)
                        sweep[lb]["noul"].append(max(c["nouls"].values()))
                        sweep[lb]["p_inv"].append(c["probs"].get("investigate", 0.0))
            elif e["type"] == "investigate":
                spots[e["spot"]["id"]] = label(e["spot"]["g"], items)
            elif e["type"] == "confirm" and e["ok"]:
                conf[(spots.get(e["id"]), e["h"])].append((e["verdict"], e["choice"], max(e["nouls"].values())))
    print("## sweep crops: max clue noul and p(investigate) by what was there")
    for lb, d in sorted(sweep.items()):
        print(f"{lb:16s} noul  {q(d['noul'])}\n{'':16s} p_inv {q(d['p_inv'])}")
    print("## confirm close-ups: verdicts by what was there and height")
    for (lb, h), v in sorted(conf.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])):
        verd = defaultdict(int)
        for x in v:
            verd[x[0]] += 1
        print(f"{str(lb):16s} {h:4.0f} m  {dict(verd)}  noul {q([x[2] for x in v])}")


if __name__ == "__main__":
    main()
