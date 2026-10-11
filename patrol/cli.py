"""patrol CLI. Subcommands:

  frames  OUT [--seed N]           save wide frames along a scripted pass plus zoom photos, with ground truth
  bench   FRAMES_DIR [--sizes ...] Clef-Flash on every saved frame at each size: latency and answers
  fly     [--seed N] [...]         closed-loop mission (see mission.py)
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

from . import clef, world
from .sim import Sim

ROOT = Path(__file__).resolve().parents[1]


def cmd_frames(a):
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    spec = world.corridor_spec(a.seed)
    (out / "scene.json").write_text(json.dumps(spec, indent=1))
    sim = Sim(spec)
    xs = [70 + 4 * k for k in range(10)] + [130 + 18 * k for k in range(10)]
    rows = []
    for k, x in enumerate(xs):
        sim.pos[:] = (x, -12, 13)
        sim.aim("inspect", world.look_target(spec, x))
        name = f"insp_{k:02d}_x{x:03d}.jpg"
        (out / name).write_bytes(sim.jpeg("inspect", 768, 576, quality=90))
        rows.append({"file": name, "camera": "inspect", "tel": sim.telemetry(),
                     "truth": sim.visible_defects("inspect", 768, 576)})
    # zoom photos at five pylons' near insulator, one of them the broken one
    for p in spec["pylons"][1:6]:
        sim.pos[:] = (p["x"] - 4, -12, 13)
        sim.set_gimbal(sim.pan, sim.tilt, zoom_target=(p["x"], world.PHASES["near"], world.ARM_Z - 0.9)); sim._sync()
        name = f"zoom_p{p['i']}.jpg"
        (out / name).write_bytes(sim.jpeg("zoom", 768, 576, quality=90))
        rows.append({"file": name, "camera": "zoom", "tel": sim.telemetry(),
                     "truth": sim.visible_defects("zoom", 768, 576)})
    sim.set_gimbal(sim.pan, sim.tilt)
    (out / "frames.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(f"{len(rows)} frames -> {out}; frames with a defect in view: {sum(1 for r in rows if r['truth'])}")


def _resize(jpeg_path: Path, w: int) -> bytes:
    import io
    from PIL import Image
    im = Image.open(jpeg_path)
    h = round(im.height * w / im.width)
    buf = io.BytesIO(); im.resize((w, h), Image.LANCZOS).save(buf, "JPEG", quality=85)
    return buf.getvalue()


def cmd_bench(a):
    d = Path(a.frames)
    rows = [json.loads(l) for l in (d / "frames.jsonl").read_text().splitlines()]
    out = Path(a.out or d / "bench.jsonl")
    if not clef.health():
        sys.exit("Clef-Flash is not answering on :8097; start it per GPU.md")
    res = []
    clef.ask(_resize(d / rows[0]["file"], 256), "warm-up")  # first call pays any cold cost
    for w in a.sizes:
        for r in rows:
            ctx = {"camera": r["camera"], "hovering": r["camera"] == "zoom"}
            dec = clef.ask(_resize(d / r["file"], w), clef.state_text(r["tel"], ctx), timeout=60)
            rec = {"size": w, "file": r["file"], "camera": r["camera"], "truth": [t["type"] for t in r["truth"]],
                   **{k: dec.to_dict()[k] for k in ("ok", "action", "confidence", "damage", "sure", "defect",
                                                     "latency_ms", "input_tokens", "error")}, "probs": dec.probs}
            res.append(rec)
            print(json.dumps({k: rec[k] for k in ("size", "file", "action", "confidence", "damage", "defect",
                                                  "latency_ms")}), flush=True)
    out.write_text("".join(json.dumps(r) + "\n" for r in res))
    print("\nsummary")
    for w in a.sizes:
        rs = [r for r in res if r["size"] == w and r["ok"]]
        lat = sorted(r["latency_ms"] for r in rs)
        pos = [r for r in rs if r["truth"]]
        neg = [r for r in rs if not r["truth"]]
        hit = sum(1 for r in pos if r["action"] != "continue" or r["damage"] >= 0.5)
        fa = sum(1 for r in neg if r["action"] != "continue" or r["damage"] >= 0.5)
        print(json.dumps({"size": w, "n": len(rs), "tokens": rs[0]["input_tokens"] if rs else 0,
                          "lat_median_ms": statistics.median(lat) if lat else None,
                          "lat_p90_ms": lat[int(0.9 * (len(lat) - 1))] if lat else None,
                          "defect_frames_noticed": f"{hit}/{len(pos)}", "clean_frames_alarmed": f"{fa}/{len(neg)}"}))


def main(argv=None):
    p = argparse.ArgumentParser(prog="patrol")
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("frames"); f.add_argument("out"); f.add_argument("--seed", type=int, default=0)
    b = sub.add_parser("bench"); b.add_argument("frames"); b.add_argument("--sizes", type=int, nargs="+",
                                                                         default=[256, 384, 512])
    b.add_argument("--out")
    fl = sub.add_parser("fly")
    from . import mission
    mission.add_args(fl)
    a = p.parse_args(argv)
    if a.cmd == "frames":
        cmd_frames(a)
    elif a.cmd == "bench":
        cmd_bench(a)
    elif a.cmd == "fly":
        mission.run_cli(a)


if __name__ == "__main__":
    main()
