"""S0, the go/no-go altitude test (rule: DECISIONS 2026-10-11 11:50, written before this ran).

Places the clue item (blue backpack) and the decoy (blue tarp) on snow and on grass, renders sweep views at 60, 40
and 20 m (wide and inspect cameras, near-nadir) and investigate close-ups (zoom camera at 20 and 12 m), and measures:
the anomaly finder's top-3 hit rate, Clef's answer on the sweep frame and on the finder's crop, and Clef's confirm on
the close-up (clue vs decoy). Ground truth is used for placement and scoring only.

usage: .venv/bin/python -m tools.altitude_probe OUT_DIR [--views 5] [--seed 0]
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from patrol import anomaly, clef, items, world  # noqa: E402
from patrol.sim import Sim  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
W, H = 512, 384
ITEMS = {  # name: (dir, real size m, role, position)
    "blue_backpack": ("assets/items/blue_backpack", 0.55, "clue", (12.0, 6.0)),
    "blue_tarp": ("assets/items/blue_tarp", 2.0, "decoy", (-28.0, -22.0)),
}
CLUE = "blue_backpack"
CLUE_WORDS = ("a blue hiking backpack lying on the ground: a bag with shoulder straps and pockets, about half a metre "
              "long")
SWEEP_Q = {
    "action": {"type": "choice", "instructions": "Search-and-rescue drone camera frame. Is anything in the picture "
               "worth flying closer to check against the missing person's belongings?",
               "criteria": {"continue": "nothing in the picture could be one of the missing person's belongings; only "
                                        "snow or grass, rocks, trees and shadows",
                            "investigate": f"something in the picture could be {CLUE_WORDS}; fly closer to check"}},
    "clue": {"type": "noul", "instructions": f"Is {CLUE_WORDS} visible anywhere in the picture?"},
    "sure": {"type": "score", "instructions": "How sure are you about what the picture shows?",
             "criteria": clef.SURE},
}
CONFIRM_Q = {
    "action": {"type": "choice", "instructions": "Close-up photo from a search drone. What is the object?",
               "criteria": {"clue": CLUE_WORDS,
                            "decoy": "something else of a similar colour that is not a backpack: a flat tarp or "
                                     "plastic sheet, a jacket, a rock or a shadow",
                            "nothing": "no object at all, only snow or grass, rocks or plants"}},
    "clue": {"type": "noul", "instructions": f"Is the object in the photo {CLUE_WORDS}, and not a tarp, a sheet or "
             "another object?"},
    "sure": {"type": "score", "instructions": "How sure are you about what the close-up shows?",
             "criteria": clef.SURE},
}
STATE = ("You are the visual spotter on a search-and-rescue drone looking for a missing hiker's belongings in open "
         "terrain. Altitude {h:.0f} m above ground; camera {cam}.")


def scene_items(terrain_seed: int) -> list[dict]:
    out = []
    for name, (d, size, role, (x, y)) in ITEMS.items():
        info = json.loads((ROOT / d / "mujoco" / "mujoco.json").read_text()) if (ROOT / d / "mujoco" / "mujoco.json").exists() \
            else items.convert(ROOT / d, size)
        out.append({"name": name, "role": role, "obj": info["obj"], "texture": info["texture"], "x": x, "y": y,
                    "yaw": random.Random(terrain_seed + len(out)).uniform(0, 360), "h": info["extent_m"][2]})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("--views", type=int, default=5)
    ap.add_argument("--summarise", action="store_true", help="rebuild SUMMARY.md from OUT/probe.jsonl, no renders"); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-clef", action="store_true", help="finder and renders only")
    ap.add_argument("--res", type=int, nargs=2, default=[512, 384], help="sweep render size (the finder's input)")
    a = ap.parse_args(argv)
    global W, H
    W, H = a.res
    out = Path(a.out); (out / "media").mkdir(parents=True, exist_ok=True)
    if a.summarise:
        return summarise([json.loads(l) for l in (out / "probe.jsonl").read_text().splitlines()], out)
    if not a.no_clef and not clef.health(timeout=20):
        sys.exit("Clef-Flash is not answering on :8097")
    rows = []
    for terrain in ("snow", "grass"):
        its = scene_items(a.seed)
        spec = world.search_spec(a.seed, terrain, its)
        sim = Sim(spec, start=(0, -100, 40))
        if not a.no_clef:
            clef.ask(sim.jpeg("wide", 256, 192), "warm-up", timeout=60)
        rng = random.Random(a.seed * 101 + (terrain == "grass"))
        for it in its:
            mid = (it["x"], it["y"], it["h"] / 2)
            for kind, cams, heights in (("sweep", ("wide", "inspect"), (60, 40, 20)), ("investigate", ("zoom",), (20, 12))):
                for h in heights:
                    for cam in cams:
                        for v in range(a.views):
                            if kind == "sweep":   # drone somewhere above, item off-centre in the frame
                                r = {"wide": 0.45, "inspect": 0.25}[cam] * h
                                dx, dy = rng.uniform(-r, r), rng.uniform(-r * 0.75, r * 0.75)
                                sim.pos[:] = (it["x"] + dx, it["y"] + dy, h)
                                sim.aim(cam, (sim.pos[0] + 0.3, sim.pos[1], 0.0))
                            else:                 # investigate: the finder's spot, aimed with up to 1 m of error
                                dx, dy = rng.uniform(-8, 8), rng.uniform(-8, 8)
                                sim.pos[:] = (it["x"] + dx, it["y"] + dy, h)
                                sim.aim(cam, (it["x"] + rng.uniform(-1, 1), it["y"] + rng.uniform(-1, 1), 0.0))
                            jpg = sim.jpeg(cam, W, H, quality=90)
                            p = sim.project(mid, cam, W, H)
                            row = {"terrain": terrain, "item": it["name"], "role": it["role"], "kind": kind,
                                   "cam": cam, "h": h, "view": v, "in_view": p is not None,
                                   "uv": [round(p[0]), round(p[1])] if p else None}
                            if v == 0:
                                (out / "media" / f"{terrain}_{it['name']}_{kind}_{cam}_{h}m.jpg").write_bytes(jpg)
                            if kind == "sweep":
                                cands = anomaly.candidates(jpg, k=3)
                                hit = next((i for i, c in enumerate(cands) if p and anomaly.contains(c, p[0], p[1])), None)
                                row.update(cands=cands, finder_rank=hit)
                                if not a.no_clef:
                                    st = STATE.format(h=h, cam=f"{cam}, pointing straight down")
                                    d = clef.ask(jpg, st, SWEEP_Q, timeout=60)
                                    row.update(frame_p_inv=round(d.probs.get("investigate", 0), 3),
                                               frame_clue=round(d.nouls.get("clue", 0), 3), frame_ms=d.latency_ms)
                                    c = cands[hit] if hit is not None else (cands[0] if cands else None)
                                    if c:
                                        dc = clef.ask(anomaly.crop(jpg, c), STATE.format(h=h, cam="crop around an odd "
                                                      "spot found by the anomaly finder"), SWEEP_Q, timeout=60)
                                        row.update(crop_of="item" if hit is not None else "top", crop_p_inv=round(
                                            dc.probs.get("investigate", 0), 3), crop_clue=round(dc.nouls.get("clue", 0), 3))
                            elif not a.no_clef:
                                d = clef.ask(jpg, STATE.format(h=h, cam="zoom, aimed at the spot") + " The drone "
                                             "has flown over an odd spot and taken this close-up.", CONFIRM_Q, timeout=60)
                                row.update(p_clue=round(d.probs.get("clue", 0), 3), p_decoy=round(d.probs.get("decoy", 0), 3),
                                           clue_noul=round(d.nouls.get("clue", 0), 3), sure=round(d.sure, 2),
                                           ms=d.latency_ms, ok=d.ok)
                            rows.append(row)
                            print(json.dumps({k: row.get(k) for k in ("terrain", "item", "kind", "cam", "h", "view",
                                              "in_view", "finder_rank", "frame_clue", "crop_clue", "p_clue",
                                              "clue_noul")}), flush=True)
        sim.close()
    (out / "probe.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    summarise(rows, out)


def summarise(rows: list[dict], out: Path):
    L = ["# S0 altitude probe", "", "## Sweep: anomaly finder top-3 hit rate (views with the item in frame)", "",
         "| terrain | item | camera | height m | finder hits | Clef frame clue noul (median) | Clef crop clue noul (median) |",
         "|---|---|---|---|---|---|---|"]
    finder_ok = {}
    for t in ("snow", "grass"):
        for it in ITEMS:
            for cam in ("wide", "inspect"):
                for h in (60, 40, 20):
                    rs = [r for r in rows if (r["terrain"], r["item"], r["kind"], r["cam"], r["h"]) == (t, it, "sweep", cam, h)]
                    iv = [r for r in rs if r["in_view"]]
                    hits = sum(r.get("finder_rank") is not None for r in iv)
                    finder_ok[(t, it, cam, h)] = len(iv) >= 4 and hits >= 4
                    med = lambda k: round(statistics.median([r[k] for r in rs if k in r]), 2) if any(k in r for r in rs) else "-"
                    L.append(f"| {t} | {it} | {cam} | {h} | {hits}/{len(iv)} | {med('frame_clue')} | {med('crop_clue')} |")
    L += ["", "## Investigate: Clef confirm on the close-up", "",
          "| terrain | item | height m | clue noul per view | p(clue) per view |", "|---|---|---|---|---|"]
    inv = {}
    for t in ("snow", "grass"):
        for it in ITEMS:
            for h in (20, 12):
                rs = [r for r in rows if (r["terrain"], r["item"], r["kind"], r["h"]) == (t, it, "investigate", h)]
                inv[(t, it, h)] = [r.get("clue_noul") for r in rs if "clue_noul" in r]
                L.append(f"| {t} | {it} | {h} | {inv[(t, it, h)]} | {[r.get('p_clue') for r in rs]} |")
    # the rule: one investigate height where a single T separates clue (>= T on 4/5) from decoy (< T on 4/5), both terrains
    verdict_inv = {}
    for h in (20, 12):   # every single threshold T that separates clue from decoy per the rule; report the range
        ok_T = [T / 100 for T in range(1, 100) if all(
            sum(v >= T / 100 for v in inv[(t, CLUE, h)]) >= 4 and sum(v < T / 100 for v in inv[(t, "blue_tarp", h)]) >= 4
            for t in ("snow", "grass"))]
        verdict_inv[h] = (min(ok_T), max(ok_T)) if ok_T else None
    sweep_by = {(cam, h): all(finder_ok[(t, it, cam, h)] for t in ("snow", "grass") for it in ITEMS)
                for cam in ("wide", "inspect") for h in (60, 40, 20)}
    inv_pass = any(v is not None for v in verdict_inv.values())
    sweep_pass = [k for k, v in sweep_by.items() if v and k[1] >= 40]
    L += ["", "## Verdict against the rule (DECISIONS 11:50)", "",
          f"- Investigate: range of single thresholds T that separate clue from decoy, per height {verdict_inv} -> {'PASS' if inv_pass else 'FAIL'}",
          f"- Sweep (finder top-3 on >= 4/5 views, both terrains, both items) by camera and height: "
          f"{ {f'{c} {h} m': v for (c, h), v in sweep_by.items()} } -> {'PASS' if sweep_pass else 'FAIL'}",
          f"- **{'GO' if inv_pass and sweep_pass else 'NO-GO' if not inv_pass else 'GO at a lower sweep height only'}**", ""]
    (out / "SUMMARY.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
