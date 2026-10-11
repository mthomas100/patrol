"""A top-down picture of a finished search run: the map features, the sector grid, the drone's path by state, every
investigated spot, the alerts with their close-ups and qwen38's notes, and the sector order qwen38 asked for. For
looking at a run and for the demo kit. The planted items are drawn as hollow squares:
that is ground truth, read here for display after the flight only.

usage: .venv/bin/python -m tools.mission_map runs/<search run> [--out PNG]     -> runs/<run>/map.png
"""
from __future__ import annotations

import argparse
import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

STATE_RGB = {"SWEEP": (60, 60, 60), "INVESTIGATE": (235, 120, 0), "RESUME": (120, 120, 200), "RETURN": (140, 60, 170),
             "TAKEOFF": (100, 100, 100), "TRANSIT": (100, 100, 100)}
PLAN_RGB = [(200, 30, 120), (20, 120, 200), (20, 150, 70), (150, 90, 10)]


def font(n):
    for f in ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc"):
        try:
            return ImageFont.truetype(f, n)
        except OSError:
            continue
    return ImageFont.load_default(size=n)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    run = Path(a.run)
    evs = [json.loads(l) for l in (run / "mission.jsonl").read_text().splitlines()]
    st = next(e for e in evs if e["type"] == "start")
    spec, area = st["spec"], st["config"]["area"]
    scene = json.loads((run / "scene.json").read_text()) if (run / "scene.json").exists() else spec
    half = spec["size"] / 2
    S, PAD, SIDE = 900, 40, 420
    k = (S - 2 * PAD) / spec["size"]
    px = lambda x, y: (PAD + (x + half) * k, PAD + (half - y) * k)      # north up
    img = Image.new("RGB", (S + SIDE, S + 170), "white")
    d = ImageDraw.Draw(img)
    f12, f14, f16, f20 = font(12), font(14), font(16), font(20)
    ground = (214, 228, 196) if spec.get("terrain") == "grass" else (236, 240, 245)
    d.rectangle([*px(-half, half), *px(half, -half)], fill=ground)
    xs, ys = [p[0] for p in area], [p[1] for p in area]
    d.rectangle([*px(min(xs), max(ys)), *px(max(xs), min(ys))], outline=(90, 90, 90), width=2)
    for s in st["sectors"]:         # the grid the thinker reorders
        x0, x1 = sorted((s["x0"], s["x1"]))
        d.rectangle([*px(x0, s["y"] + s["h"] / 2), *px(x1, s["y"] - s["h"] / 2)], outline=(170, 170, 170))
        d.text(px(x0 + 1.5, s["y"] + s["h"] / 2 - 1.5), s["id"], fill=(130, 130, 130), font=f12)
    m = spec.get("map", {})
    if m.get("stream"):
        d.line([px(*p) for p in m["stream"]], fill=(70, 140, 220), width=5)
    if m.get("trail"):
        d.line([px(*p) for p in m["trail"]], fill=(150, 110, 60), width=4)
    if m.get("lkp"):
        x, y = px(*m["lkp"])
        d.polygon([(x, y - 10), (x - 9, y + 7), (x + 9, y + 7)], fill=(0, 0, 0))
        d.text((x + 12, y - 8), "trailhead (last known point)", fill=(0, 0, 0), font=f14)
    ticks = [e for e in evs if e["type"] == "tick"]
    for a_, b_ in zip(ticks, ticks[1:]):
        d.line([px(a_["tel"]["x"], a_["tel"]["y"]), px(b_["tel"]["x"], b_["tel"]["y"])],
               fill=STATE_RGB.get(b_["state"], (60, 60, 60)), width=2)
    for it in scene.get("items", []):   # ground truth, display only
        x, y = px(it["x"], it["y"])
        col = (0, 140, 0) if it["role"] == "clue" else (0, 0, 0)
        d.rectangle([x - 7, y - 7, x + 7, y + 7], outline=col, width=2)
        d.text((x + 9, y + 4), it["name"].replace("_", " "), fill=col, font=f12)
    for e in evs:
        if e["type"] == "dismiss" and e.get("g"):
            x, y = px(*e["g"])
            d.line([(x - 6, y - 6), (x + 6, y + 6)], fill=(110, 110, 110), width=3)
            d.line([(x - 6, y + 6), (x + 6, y - 6)], fill=(110, 110, 110), width=3)
    alerts = [e for e in evs if e["type"] == "alert"]
    for e in alerts:
        x, y = px(*e["g"])
        d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=(220, 20, 20), outline=(255, 255, 255), width=2)
        d.text((x + 12, y - 20), f"{e['id']} {e['family']} ({e['t']:.0f} s)", fill=(190, 0, 0), font=f16)
    plans = [e for e in evs if e["type"] == "plan" and e.get("applied")]
    for j, p in enumerate(plans):       # numbered sector order per applied plan
        col = PLAN_RGB[j % len(PLAN_RGB)]
        secs = {s["id"]: s for s in st["sectors"]}
        for n, sid in enumerate(p.get("first", []), 1):
            s = secs[sid]
            cx, cy = px((s["x0"] + s["x1"]) / 2 + (j - 1) * 5, s["y"])
            d.ellipse([cx - 11, cy - 11, cx + 11, cy + 11], fill=col)
            d.text((cx - 4, cy - 8), str(n), fill="white", font=f14)
    # legend and title
    summ = next((e for e in evs if e["type"] == "summary"), {})
    sc = json.loads((run / "score.json").read_text()) if (run / "score.json").exists() else {}
    d.text((PAD, 8), f"{run.name}: {spec.get('terrain')} seed {spec.get('seed')}, recall {sc.get('recall', '?')}, "
           f"false alerts {len(sc.get('false_alerts', []))}, mission {summ.get('sim_s', '?')} s sim / "
           f"{summ.get('wall_s', '?')} s wall", fill=(0, 0, 0), font=f20)
    y0 = S + 5
    leg = [("sweep path", STATE_RGB["SWEEP"]), ("investigate", STATE_RGB["INVESTIGATE"]),
           ("return", STATE_RGB["RETURN"]), ("trail", (150, 110, 60)), ("stream", (70, 140, 220))]
    x = PAD
    for name, col in leg:
        d.line([(x, y0 + 10), (x + 30, y0 + 10)], fill=col, width=4)
        d.text((x + 36, y0 + 2), name, fill=(0, 0, 0), font=f14); x += 140
    d.text((PAD, y0 + 24), "red dot: alert   grey x: investigated and dismissed   squares: planted items (green clue, "
           "black decoy; truth, display only)   numbered dots: qwen38's sector order after each find",
           fill=(60, 60, 60), font=f12)
    yy = y0 + 46
    for j, p in enumerate(plans):
        d.text((PAD, yy), f"plan {j + 1} (t {p['t']:.0f} s): {', '.join(p.get('first', []))}: "
               f"{p.get('reason', '')}"[:150], fill=PLAN_RGB[j % len(PLAN_RGB)], font=f14)
        yy += 20
    # side panel: each alert's close-up and qwen38's radio note
    notes = {e["id"]: e for e in evs if e["type"] == "note"}
    sx, sy = S + 10, 40
    for e in alerts:
        ph = run / e["photo"]
        if ph.exists():
            t = Image.open(ph).convert("RGB")
            t.thumbnail((SIDE - 20, 170))
            img.paste(t, (sx, sy))
            sy += t.height + 4
        n = notes.get(e["id"], {})
        txt = f"{e['id']} {e['family']}, conf {e['conf']:.2f} at {e['h']:.0f} m, by {e['by']}. " + \
            (f"qwen38: {n.get('alert', '')} {n.get('check', '')}" if n.get("alert") else "")
        for line in textwrap.wrap(txt, 52)[:6]:
            d.text((sx, sy), line, fill=(0, 0, 0), font=f14); sy += 18
        sy += 12
    out = Path(a.out) if a.out else run / "map.png"
    img.save(out)
    print(out)


if __name__ == "__main__":
    main()
