"""The live-vs-after comparison (BRIEF, the core claim): the same flight scored two ways.

Live: what the drone alerted during the flight, investigating odd spots with the zoom close-up (summary.json).
After: only the sweep-height photos the drone brought home, analysed after landing with the same Clef: the same
anomaly finder on every saved frame (more candidates than the live loop had time for: k=6), each crop asked the
confirm question (the strongest question there is, with no close-up to ask it of), an alert when Clef picks a clue
with its noul >= T_CONFIRM (the live confirm bar), one alert per clue within ALERT_R. Then both are scored against the
planted items (scoring only). Writes RUN/after/after.json and prints one summary line; `--md` adds a table row.

usage: .venv/bin/python -m tools.after_landing runs/<search run> [more runs] [--out runs/s6-live-vs-after]
"""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

from patrol import anomaly, clef, clues as cluelib, search

ROOT = Path(__file__).resolve().parents[1]
K = 6
T_CONFIRM = 0.5
ALERT_R = 6.0


def after(run: Path) -> dict:
    evs = [json.loads(l) for l in (run / "mission.jsonl").read_text().splitlines()]
    st = next(e for e in evs if e["type"] == "start")
    cl = st["clues"]
    names = [c["name"] for c in cl]
    frames = [e for e in evs if e["type"] == "frame"]
    alerts, asked, t0 = [], 0, time.time()
    lat = []
    from patrol import geo
    for f in frames:
        jpg = (run / f["frame"]).read_bytes()
        for c in anomaly.candidates(jpg, k=K):
            g = geo.pixel_to_ground(c["cx"], c["cy"], f["W"], f["H"], f["pose"])
            if not g:
                continue
            dec = clef.ask(anomaly.crop(jpg, c), cluelib.confirm_state(f["pose"]["pos"][2]), cluelib.confirm_schema(cl),
                           timeout=20.0)
            asked += 1
            lat.append(dec.latency_ms)
            if not dec.ok or dec.action not in names:
                continue
            noul = dec.nouls.get(dec.action, 0.0)
            if noul < T_CONFIRM:
                continue
            if any(a["clue"] == dec.action and math.dist(a["g"], g) < ALERT_R for a in alerts):
                continue
            fam = next(x["family"] for x in cl if x["name"] == dec.action)
            alerts.append({"id": f"P{len(alerts) + 1}", "clue": dec.action, "family": fam, "g": [round(g[0], 2),
                           round(g[1], 2)], "conf": round(noul, 3), "frame": f["frame"], "t": f["t"]})
    return {"alerts": alerts, "asked": asked, "frames": len(frames), "wall_s": round(time.time() - t0, 1),
            "clef_median_ms": sorted(lat)[len(lat) // 2] if lat else None}


def score_alerts(run: Path, alerts: list[dict], match_r: float = 5.0) -> dict:
    items = json.loads((run / "scene.json").read_text())["items"]
    found, true_ids = [], set()
    for it in items:
        if it["role"] != "clue":
            continue
        hit = [a for a in alerts if math.dist(a["g"], (it["x"], it["y"])) < match_r and search._same_item(a, it["name"])]
        if hit:
            found.append(it["name"]); true_ids |= {a["id"] for a in hit}
    return {"found": found, "clues": sum(it["role"] == "clue" for it in items),
            "false_alerts": [a["id"] + " " + a["clue"] for a in alerts if a["id"] not in true_ids]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--out", help="also append a row per run to OUT/rows.jsonl")
    a = ap.parse_args(argv)
    for r in map(Path, a.runs):
        s = json.loads((r / "summary.json").read_text())
        live = score_alerts(r, s["alerts"])
        aft = after(r)
        aft_sc = score_alerts(r, aft["alerts"])
        batt = s.get("battery_used_pct") or 0
        row = {"run": str(r), "clues": live["clues"], "live_found": live["found"], "live_false": live["false_alerts"],
               "after_found": aft_sc["found"], "after_false": aft_sc["false_alerts"], "battery_pct": batt,
               "live_per_battery": round(len(live["found"]) / batt * 100, 2) if batt else None,
               "after_per_battery": round(len(aft_sc["found"]) / batt * 100, 2) if batt else None,
               "after_asked": aft["asked"], "after_wall_s": aft["wall_s"], "after_clef_median_ms": aft["clef_median_ms"]}
        (r / "after").mkdir(exist_ok=True)
        (r / "after" / "after.json").write_text(json.dumps(aft | {"score": aft_sc}, indent=1))
        print(json.dumps(row), flush=True)
        if a.out:
            Path(a.out).mkdir(parents=True, exist_ok=True)
            with open(Path(a.out) / "rows.jsonl", "a") as f:
                f.write(json.dumps(row) + "\n")


if __name__ == "__main__":
    main()
