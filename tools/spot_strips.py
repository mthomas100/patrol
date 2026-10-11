"""One picture per investigated spot of a search run: the sweep frame with the finder's box, the crop Clef judged, and
each zoom close-up with its verdict. For looking at a run.

usage: .venv/bin/python -m tools.spot_strips runs/<search run>     -> runs/<run>/strips/S1.jpg ...
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw


def main(argv=None):
    run = Path((argv or sys.argv[1:])[0])
    evs = [json.loads(l) for l in (run / "mission.jsonl").read_text().splitlines()]
    alerts = {e["spot"]: e for e in evs if e["type"] == "alert"}
    (run / "strips").mkdir(exist_ok=True)
    for spot in [e["spot"] for e in evs if e["type"] == "investigate"]:
        tiles = []
        if spot.get("frame"):
            fr = Image.open(run / spot["frame"]).convert("RGB")
            x0, y0, x1, y1 = spot["box"]
            ImageDraw.Draw(fr).rectangle([x0 - 6, y0 - 6, x1 + 6, y1 + 6], outline=(255, 170, 0), width=6)
            tiles.append((fr.resize((640, 480)), f"sweep frame from {spot['sweep_h']:.0f} m, finder box"))
        if spot.get("crop"):
            tiles.append((Image.open(run / spot["crop"]).convert("RGB").resize((480, 480)),
                          f"crop for Clef: {spot['clue']} {spot['noul']:.0%}"))
        for c in [e for e in evs if e["type"] == "confirm" and e["id"] == spot["id"]]:
            tiles.append((Image.open(run / c["photo"]).convert("RGB").resize((640, 480)),
                          f"zoom at {c['h']:.0f} m: {c['verdict']} ({c['clue']} {c['noul']:.0%}, chose {c['choice']})"))
        a = alerts.get(spot["id"])
        head = f"{spot['id']}: " + (f"ALERT {a['id']} {a['family']} at ({a['g'][0]:.0f}, {a['g'][1]:.0f})" if a
                                    else "dismissed")
        W = sum(t[0].width for t in tiles) + 20 * (len(tiles) + 1)
        out = Image.new("RGB", (W, 580), (20, 22, 26))
        d = ImageDraw.Draw(out)
        d.text((20, 8), head, fill=(255, 210, 120) if a else (200, 200, 200))
        x = 20
        for im, cap in tiles:
            out.paste(im, (x, 80)); d.text((x, 50), cap, fill=(235, 235, 235)); x += im.width + 20
        out.save(run / "strips" / f"{spot['id']}.jpg", quality=88)
        print(run / "strips" / f"{spot['id']}.jpg", head)


if __name__ == "__main__":
    main()
