"""Probe Clef-Flash's cruise signal on mid-span defects (frayed conductor, hanging debris) against clean spans.

For each seed, the drone is placed along the approach to each mid-span defect and to clean span points, the inspect
gimbal is aimed the way the mission aims it (near conductor 9 m ahead), and Clef answers the cruise schema in
several frame variants. The output says, per variant, how many defect approaches would trigger a hover and how many
clean frames would, plus latency.

usage: .venv/bin/python -m tools.span_probe OUT_DIR [--seeds 0 1 2] [--variants base tele hires parts]
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from patrol import clef, world  # noqa: E402
from patrol.control import LOOK_GAIN  # noqa: E402
from patrol.sim import Sim  # noqa: E402

VARIANTS = {   # name: (camera, width, height, extra component questions)
    "base": ("inspect", 512, 384, False),   # what the mission flies today
    "tele": ("zoom", 512, 384, False),      # 24-degree gimbal camera on the same aim point
    "hires": ("inspect", 768, 576, False),  # more pixels, more tokens
    "parts": ("inspect", 512, 384, True),   # today's frame plus the four component questions of the confirm schema
}


def cruise_questions(parts: bool) -> dict:
    q = clef.schema()
    if parts:
        q.update({k: {"type": "noul", "instructions": v} for k, v in clef.COMPONENT_NOULS.items()})
    return q


def points(spec: dict, rng: random.Random) -> list[dict]:
    """Approach points: each mid-span defect, and three clean span points away from any defect and tower."""
    out = [{"what": d["id"] + ":" + d["type"], "x": d["x"], "defect": d["id"]} for d in spec["defects"]
           if d["type"] in ("frayed_conductor", "foreign_object") and d.get("where", "span") == "span"]
    busy = [d["x"] for d in spec["defects"]]
    while len(out) < 5:
        x = rng.uniform(20, spec["length"] - 20)
        if min(abs(x - b) for b in busy) > 25 and abs(x - round(x / spec["spacing"]) * spec["spacing"]) > 15:
            out.append({"what": "clean", "x": round(x, 1), "defect": None}); busy.append(x)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--variants", nargs="+", default=list(VARIANTS))
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    if not clef.health(timeout=20):
        sys.exit("Clef-Flash is not answering on :8097")
    rows, warm = [], False
    for seed in a.seeds:
        spec = world.m2_spec(seed)
        sim = Sim(spec)
        if not warm:      # the first call pays any cold cost; keep it out of the latency numbers
            clef.ask(sim.jpeg("inspect", 256, 192), "warm-up", timeout=60); warm = True
        rng = random.Random(seed + 7)
        for p in points(spec, rng):
            for dx in (-18, -15, -12, -9, -6, -3, 0):
                x = p["x"] + dx
                sim.pos[:] = (x, -12, 13); sim.vel[:] = (3.0, 0, 0)
                aim = world.look_target(spec, x)
                if any(abs(py["x"] - aim[0]) < 0.5 for py in spec["pylons"]):
                    continue          # the mission aims at a tower here; towers are photographed anyway
                for v in a.variants:
                    cam, w, h, parts = VARIANTS[v]
                    sim.aim(cam, aim)
                    jpg = sim.jpeg(cam, w, h)
                    truth = [t for t in sim.visible_defects(cam, w, h, max_depth=40) if t["id"] == p["defect"]]
                    d = clef.ask(jpg, clef.state_text(sim.telemetry(), {"length": spec["length"]}),
                                 cruise_questions(parts), timeout=60)
                    pl = d.probs.get("hover_and_photograph", 0) + d.probs.get("flag_damage", 0)
                    parts_max = max((d.nouls.get(k, 0) for k in clef.COMPONENT_NOULS), default=0)
                    r = {"seed": seed, "what": p["what"], "dx": dx, "variant": v, "in_view": bool(truth),
                         "depth": truth[0]["depth"] if truth else None, "ok": d.ok, "latency_ms": d.latency_ms,
                         "tokens": d.input_tokens, "p_continue": d.probs.get("continue", 0), "p_look": round(pl, 3),
                         "trigger": LOOK_GAIN * pl > d.probs.get("continue", 0), "damage": round(d.damage, 3),
                         "sure": round(d.sure, 2), "defect": d.defect, "parts_max": round(parts_max, 3),
                         "nouls": {k: round(v2, 3) for k, v2 in d.nouls.items()}}
                    rows.append(r)
                    print(json.dumps({k: r[k] for k in ("seed", "what", "dx", "variant", "in_view", "p_look",
                                                        "trigger", "damage", "parts_max", "latency_ms")}), flush=True)
        sim.close()
    (out / "probe.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    print("\nsummary (per variant: approaches with at least one trigger while in view; clean frames triggered)")
    for v in a.variants:
        rs = [r for r in rows if r["variant"] == v and r["ok"]]
        appr = {}
        for r in rs:
            if r["what"] != "clean" and r["in_view"]:
                appr.setdefault((r["seed"], r["what"]), []).append(r)
        clean = [r for r in rs if r["what"] == "clean"]
        lat = sorted(r["latency_ms"] for r in rs)
        dmg_thr = max([r["damage"] for r in clean] + [0])
        print(json.dumps({
            "variant": v, "frames": len(rs), "tokens": rs[0]["tokens"] if rs else None,
            "lat_median_ms": statistics.median(lat) if lat else None,
            "approaches_triggered": f"{sum(any(r['trigger'] for r in g) for g in appr.values())}/{len(appr)}",
            "clean_triggered": f"{sum(r['trigger'] for r in clean)}/{len(clean)}",
            "max_clean_damage": dmg_thr,
            "approaches_damage_above_clean_max": f"{sum(any(r['damage'] > dmg_thr for r in g) for g in appr.values())}/{len(appr)}",
            "max_clean_parts": max([r["parts_max"] for r in clean] + [0]),
            "per_approach_max_p_look": {f"s{k[0]}:{k[1]}": max(r["p_look"] for r in g) for k, g in appr.items()},
            "clean_max_p_look": max([r["p_look"] for r in clean] + [0]),
        }))


if __name__ == "__main__":
    main()
