"""Probe Clef-Flash on the M2 scene: per-defect-type cruise signal, a 'where in the frame' question, zoom confirms.

usage: .venv/bin/python -m tools.m2_probe OUT_DIR [--seed 0]   (writes probe.jsonl and prints a summary)
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from patrol import clef, world  # noqa: E402
from patrol.sim import Sim  # noqa: E402

W, H = 512, 384

# Measured useless on 2026-10-11 (4/30 correct, mostly "nothing"); kept here for the record, not in the product.
WHERE_QUESTION = {
    "type": "choice",
    "instructions": "Where in the picture is the most unusual or suspicious thing on the line equipment?",
    "criteria": {"left": "in the left third of the picture",
                 "centre": "in the middle third of the picture",
                 "right": "in the right third of the picture",
                 "nothing": "nothing unusual anywhere in the picture"},
}




def where_truth(u):
    return "left" if u < W / 3 else ("right" if u > 2 * W / 3 else "centre")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--zoom-fovs", type=float, nargs="+", default=[16, 24])
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    spec = world.m2_spec(a.seed)
    sim = Sim(spec)
    q = clef.schema()
    q["where"] = WHERE_QUESTION
    rows = []
    # cruise frames: each defect at five along-track offsets from the aim point, plus clean frames
    cases = [(d, d["x"] - 9 + o) for d in spec["defects"] for o in (-4, -2, 0, 2, 4)]
    clean_x = [12, 60, 150, 170, 235, 280, 290]
    cases += [(None, x) for x in clean_x]
    for d, x in cases:
        sim.pos[:] = (x, -12, 13)
        lt = world.look_target(spec, x)
        sim.aim("inspect", lt)
        jpg = sim.jpeg("inspect", W, H)
        truth = sim.visible_defects("inspect", W, H)
        dec = clef.ask(jpg, clef.state_text(sim.telemetry(), {}), q, timeout=60)
        r = {"kind": "cruise", "x": x, "defect": d["type"] if d else None, "id": d["id"] if d else None,
             "in_frame": bool(truth), "where_truth": where_truth(truth[0]["u"]) if truth else "nothing",
             "probs": dec.probs, "damage": dec.damage, "where": dec.extra.get("where"),
             "nouls": dec.nouls, "latency_ms": dec.latency_ms, "ok": dec.ok}
        rows.append(r); print(json.dumps({k: r[k] for k in ("x", "defect", "where_truth", "where", "latency_ms")}),
                              flush=True)
    # zoom confirms: aimed at the defect, and 2 and 4 m off along track, at each fov
    for fov in a.zoom_fovs:
        sim.model.cam_fovy[sim.cam["zoom"]] = fov
        for d in spec["defects"]:
            for off in (0, 2, 4):
                sim.pos[:] = (d["x"] - 9, -12, 13)
                sim.aim("zoom", (d["x"] + off, d["y"], d["z"]))
                jpg = sim.jpeg("zoom", W, H)
                if off == 0:
                    (out / f"zoom{int(fov)}_{d['id']}_{d['type']}.jpg").write_bytes(jpg)
                dec = clef.ask(jpg, clef.state_text(sim.telemetry(), {"camera": "zoom", "hovering": True}),
                               clef.confirm_schema(), timeout=60)
                rows.append({"kind": "zoom", "fov": fov, "off": off, "defect": d["type"], "id": d["id"],
                             "in_frame": bool(sim.visible_defects("zoom", W, H, 40)),
                             "flag": dec.probs.get("flag_damage"), "nouls": dec.nouls, "ok": dec.ok,
                             "latency_ms": dec.latency_ms})
        for x in clean_x[:4]:
            sim.pos[:] = (x, -12, 13)
            sim.aim("zoom", world.look_target(spec, x))
            dec = clef.ask(sim.jpeg("zoom", W, H), clef.state_text(sim.telemetry(), {"camera": "zoom",
                                                                                     "hovering": True}),
                           clef.confirm_schema(), timeout=60)
            rows.append({"kind": "zoom", "fov": fov, "off": None, "defect": None, "flag": dec.probs.get("flag_damage"),
                         "nouls": dec.nouls, "ok": dec.ok, "latency_ms": dec.latency_ms})
    (out / "probe.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    # summary
    print("\n== cruise: hover+flag probability by defect type (in frame) vs clean")
    by = {}
    for r in rows:
        if r["kind"] == "cruise" and r["ok"]:
            k = (r["defect"] or "clean_but_defect_in_view") if r["in_frame"] else ("clean" if r["defect"] is None else "out_of_frame")
            p = r["probs"].get("hover_and_photograph", 0) + r["probs"].get("flag_damage", 0)
            by.setdefault(k, []).append(round(p, 2))
    for k, v in by.items():
        print(f"  {k:18s} n={len(v)} min {min(v):.2f} mean {statistics.mean(v):.2f} max {max(v):.2f}")
    cr = [r for r in rows if r["kind"] == "cruise" and r["ok"] and r["in_frame"]]
    print(f"== where correct on in-frame defects: {sum(r['where'] == r['where_truth'] for r in cr)}/{len(cr)}")
    print("== zoom flag probability")
    for r in rows:
        if r["kind"] == "zoom":
            print(f"  fov {r['fov']:.0f} {str(r['defect']):18s} off {r['off']} in_frame {r.get('in_frame')} "
                  f"flag {r['flag']:.2f}")


if __name__ == "__main__":
    main()
