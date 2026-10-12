"""S7 step 1: offline probe of the finder and Clef on real aerial photos (HERIDAL test split, person boxes).

Per image, two finder views, both 1280x960 like the simulator's sweep frame:
  native  16 overlapping 1280x960 tiles of the 4000x3000 photo (2 cm/px, about the sim sweep at 32 m)
  down    the whole photo resized to 1280x960 (6.25 cm/px, about the sim sweep at 100 m)
The finder (patrol/anomaly.py, unchanged) proposes up to 10 boxes per frame (recall@3 is what a flight uses). Clef asks
the flight's own sweep question (clues.sweep_schema) about each top-3 crop and about a crop centred on every person box
(the positive control, independent of the finder), and the confirm question (clues.confirm_schema) about a native-pixel
close-up framed like the flight's zoom (zoom_frame x 1.7 m) for every crop that passes the flight's sweep gate and for
every person. Clef calls pause while a scored flight runs (pgrep), so the probe never skews another stream's timings.

usage: .venv/bin/python tools/real_probe.py --split tuning [--limit N] [--no-clef] [--out runs/s7-probe/tuning]
       .venv/bin/python tools/real_probe.py --summarise runs/s7-probe/tuning
"""
from __future__ import annotations

import argparse
import io
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from patrol import anomaly, clef, clues, real  # noqa: E402
from patrol.search import SearchConfig  # noqa: E402

W, H = 1280, 960
K_FIND, K_ASK = 10, 3
H_EQ = {"native": 32.0, "down": 100.0}      # sim sweep height with the same metres per pixel (2.5 cm/px at 40 m)
CFG = SearchConfig()
CL = [real.PERSON]


def flying() -> bool:
    return subprocess.run(["pgrep", "-f", "patrol.cli search|e2e_search"], capture_output=True).returncode == 0


def ask(jpg: bytes, state: str, q: dict) -> dict:
    waited = 0.0
    while flying():
        time.sleep(10); waited += 10
    d = clef.ask(jpg, state, q, timeout=20.0)
    if not d.ok:                                  # the keeper restarts Clef within about a minute
        for _ in range(12):
            time.sleep(10)
            d = clef.ask(jpg, state, q, timeout=20.0)
            if d.ok:
                break
    return {"ok": d.ok, "action": d.action, "probs": d.probs, "nouls": d.nouls, "sure": round(d.sure, 3),
            "ms": d.latency_ms, "waited_s": waited, **({"error": d.error} if not d.ok else {})}


def sweep_gate(r: dict) -> bool:
    nb, p = r["nouls"].get("person", 0.0), r["probs"].get("investigate", 0.0)
    return r["ok"] and (nb >= CFG.inv_noul or p >= CFG.inv_p or (nb >= CFG.inv_noul_weak and p >= CFG.inv_p_weak))


def confirm_gate(r: dict) -> bool:
    return r["ok"] and r["action"] == "person" and r["nouls"].get("person", 0.0) >= CFG.t_confirm


def frames(a: np.ndarray):
    """(view, frame array, scale, x off, y off): frame pixel (u, v) is native (x + u * scale, y + v * scale)."""
    Hn, Wn = a.shape[:2]
    for y in np.linspace(0, Hn - H, 4).astype(int):
        for x in np.linspace(0, Wn - W, 4).astype(int):
            yield "native", a[y:y + H, x:x + W], 1.0, int(x), int(y)
    s = Wn / W
    yield "down", np.asarray(Image.fromarray(a).resize((W, round(Hn / s)), Image.LANCZOS)), s, 0, 0


def hit(c: dict, b: dict, s: float, x: int, y: int) -> bool:
    """The candidate box (frame pixels) overlaps the person box (native pixels)."""
    cx0, cy0, cx1, cy1 = x + c["x0"] * s, y + c["y0"] * s, x + c["x1"] * s, y + c["y1"] * s
    return cx0 <= b["x1"] and b["x0"] <= cx1 and cy0 <= b["y1"] and b["y0"] <= cy1


def in_frame(b: dict, f: np.ndarray, s: float, x: int, y: int) -> bool:
    """The person box lies wholly inside this frame."""
    fh, fw = f.shape[:2]
    return b["x0"] >= x and b["y0"] >= y and b["x1"] <= x + fw * s and b["y1"] <= y + fh * s


def closeup(a: np.ndarray, gx: float, gy: float) -> bytes:
    """Native pixels around (gx, gy), framed like the flight's zoom: zoom_frame x the clue size, 4:3, 512x384."""
    foot = max(CFG.zoom_foot_min, CFG.zoom_frame * real.PERSON["size_m"]) / real.GSD_M      # ground height, px
    hh, hw = foot / 2, foot * 2 / 3
    Hn, Wn = a.shape[:2]
    x0, y0 = int(max(0, min(Wn - 2 * hw, gx - hw))), int(max(0, min(Hn - 2 * hh, gy - hh)))
    im = Image.fromarray(a[y0:y0 + int(2 * hh), x0:x0 + int(2 * hw)]).resize((CFG.zoom_w, CFG.zoom_h), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def probe(item: dict, use_clef: bool, crops_dir: Path | None) -> dict:
    a = np.asarray(Image.open(item["jpg"]).convert("RGB"))
    t0 = time.perf_counter()
    rows, persons = [], [{"box": b, "views": {}} for b in item["boxes"]]
    for view, f, s, x, y in frames(a):
        t = time.perf_counter()
        cands = anomaly.candidates(f, k=K_FIND)
        fms = round((time.perf_counter() - t) * 1000, 1)
        for rank, c in enumerate(cands):
            on = [i for i, p in enumerate(persons) if hit(c, p["box"], s, x, y)]
            g = (x + (c["x0"] + c["x1"]) / 2 * s, y + (c["y0"] + c["y1"]) / 2 * s)
            row = {"view": view, "tile": [x, y], "rank": rank, "box": [c[k] for k in ("x0", "y0", "x1", "y1")],
                   "area": c["area"], "g": [round(g[0]), round(g[1])], "person": on, "finder_ms": fms}
            if use_clef and rank < K_ASK:
                crop = anomaly.crop(f, c)
                row["sweep"] = ask(crop, clues.sweep_state(H_EQ[view]), clues.sweep_schema(CL))
                row["gate"] = sweep_gate(row["sweep"])
                if row["gate"]:
                    row["confirm"] = ask(closeup(a, *g), clues.confirm_state(CFG.steps[0]), clues.confirm_schema(CL))
                    row["alert"] = confirm_gate(row["confirm"])
                if crops_dir and (on or row["gate"]):
                    (crops_dir / f"{item['stem']}_{view}_{x}_{y}_r{rank}.jpg").write_bytes(crop)
            rows.append(row)
        for p in persons:                 # the positive control: Clef on a crop centred on the person, per view
            b = p["box"]
            if not in_frame(b, f, s, x, y) or view in p["views"]:
                continue
            fb = {"x0": int((b["x0"] - x) / s), "y0": int((b["y0"] - y) / s), "x1": int((b["x1"] - x) / s),
                  "y1": int((b["y1"] - y) / s)}
            v = {"px": [fb["x1"] - fb["x0"], fb["y1"] - fb["y0"]]}
            if use_clef:
                v["sweep"] = ask(anomaly.crop(f, fb), clues.sweep_state(H_EQ[view]), clues.sweep_schema(CL))
                v["gate"] = sweep_gate(v["sweep"])
            p["views"][view] = v
    if use_clef:
        for p in persons:
            b = p["box"]
            p["confirm"] = ask(closeup(a, (b["x0"] + b["x1"]) / 2, (b["y0"] + b["y1"]) / 2),
                               clues.confirm_state(CFG.steps[0]), clues.confirm_schema(CL))
            p["alert"] = confirm_gate(p["confirm"])
    return {"stem": item["stem"], "split": item["split"], "persons": persons, "cands": rows,
            "wall_s": round(time.perf_counter() - t0, 1)}


NEAR_PX = 150           # 3 m at 2 cm/px: an alert this close to a person box is on that person or their shadow


def _dist_px(g, b: dict) -> float:
    """Distance from a native point to a box (0 inside)."""
    dx, dy = max(b["x0"] - g[0], 0, g[0] - b["x1"]), max(b["y0"] - g[1], 0, g[1] - b["y1"])
    return (dx * dx + dy * dy) ** 0.5


def _pct(a, b):
    return f"{a}/{b} ({100 * a / b:.0f}%)" if b else "0/0"


def summarise(out: Path) -> str:
    recs = [json.loads(l) for l in (out / "probe.jsonl").read_text().splitlines() if l.strip()]
    n_img, n_per = len(recs), sum(len(r["persons"]) for r in recs)
    L = [f"# S7 probe: {out.name} ({n_img} images, {n_per} persons)", ""]
    L.append("## Finder recall on person boxes (a person counts when any candidate box overlaps it)")
    L.append("| view | recall@3 | recall@5 | recall@10 | finder ms per 1280x960 frame (median) |")
    L.append("|---|---|---|---|---|")
    for view in ("native", "down"):
        found = {k: 0 for k in (3, 5, 10)}
        for r in recs:
            for i, _ in enumerate(r["persons"]):
                ranks = [c["rank"] for c in r["cands"] if c["view"] == view and i in c["person"]]
                for k in found:
                    found[k] += bool(ranks) and min(ranks) < k
        ms = statistics.median([c["finder_ms"] for r in recs for c in r["cands"] if c["view"] == view] or [0])
        L.append(f"| {view} | {_pct(found[3], n_per)} | {_pct(found[5], n_per)} | {_pct(found[10], n_per)} | {ms:.0f} |")
    swept = [c for r in recs for c in r["cands"] if "sweep" in c]
    if swept:
        L += ["", "## Clef sweep question (clues.sweep_schema with the person clue), flight gate unchanged"]
        L.append("| view | crops | person noul median (max) | p(investigate) median | pass the sweep gate |")
        L.append("|---|---|---|---|---|")
        for view in ("native", "down"):
            for kind, sel in (("finder crop on a person", lambda c: c["person"]),
                              ("finder crop, background", lambda c: not c["person"])):
                cs = [c for c in swept if c["view"] == view and sel(c)]
                ctl = []
                if kind.endswith("person"):
                    ctl = [p["views"][view] for r in recs for p in r["persons"] if "sweep" in p["views"].get(view, {})]
                for label, rows in ((kind, cs), (f"centred on a person (control)", ctl) if ctl else (None, None)):
                    if not rows:
                        continue
                    nl = [x["sweep"]["nouls"].get("person", 0) for x in rows]
                    pi = [x["sweep"]["probs"].get("investigate", 0) for x in rows]
                    L.append(f"| {view} | {label}: {len(rows)} | {statistics.median(nl):.3f} ({max(nl):.3f}) | "
                             f"{statistics.median(pi):.3f} | {_pct(sum(x['gate'] for x in rows), len(rows))} |")
        conf_bg = [c for c in swept if not c["person"] and "confirm" in c]
        conf_p = [c for c in swept if c["person"] and "confirm" in c]
        conf_ctl = [p for r in recs for p in r["persons"] if "confirm" in p]
        L += ["", "## Clef confirm question on a native close-up (clues.confirm_schema, t_confirm "
              f"{CFG.t_confirm})", "| close-up of | n | alert (choice person and noul >= bar) | noul median |",
              "|---|---|---|---|"]
        for label, rows in (("every person (control)", conf_ctl), ("finder spots on a person, gate passed", conf_p),
                            ("finder spots on background, gate passed", conf_bg)):
            if rows:
                nl = [x["confirm"]["nouls"].get("person", 0) for x in rows]
                L.append(f"| {label} | {len(rows)} | {_pct(sum(x['alert'] for x in rows), len(rows))} | "
                         f"{statistics.median(nl):.3f} |")
        for view in ("native", "down"):
            fa = sum(c.get("alert", False) for c in swept if c["view"] == view and not c["person"])
            far = sum(c.get("alert", False) and all(_dist_px(c["g"], p["box"]) > NEAR_PX for p in r["persons"])
                      for r in recs for c in r["cands"] if c["view"] == view and not c["person"])
            found = sum(any(c.get("alert") and i in c["person"] for c in r["cands"] if c["view"] == view)
                        for r in recs for i in range(len(r["persons"])))
            L.append(f"\n{view}: alerts off every person box {fa} on {n_img} images ({fa / n_img:.2f} per image), of "
                     f"which {far} more than {NEAR_PX * real.GSD_M:.0f} m from any box; persons found end to end "
                     f"(finder top 3, sweep gate, confirm) {_pct(found, n_per)}")
        lat = [x["ms"] for c in swept for x in [c["sweep"]] + ([c["confirm"]] if "confirm" in c else []) if x["ok"]]
        bad = sum(not x["ok"] for c in swept for x in [c["sweep"]] + ([c["confirm"]] if "confirm" in c else []))
        L.append(f"\nClef latency median {statistics.median(lat):.0f} ms, p90 {np.percentile(lat, 90):.0f} ms over "
                 f"{len(lat)} calls; {bad} failed calls; wall {sum(r['wall_s'] for r in recs) / 60:.1f} min")
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["tuning", "held_out"], default="tuning")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--no-clef", action="store_true")
    ap.add_argument("--out", default="")
    ap.add_argument("--summarise", default="")
    a = ap.parse_args(argv)
    if a.summarise:
        print(summarise(Path(a.summarise)), end="")
        return 0
    out = Path(a.out or f"runs/s7-probe/{a.split}").resolve()
    (out / "crops").mkdir(parents=True, exist_ok=True)
    items = real.images(a.split)[: a.limit or None]
    done = set()
    jl = out / "probe.jsonl"
    if jl.exists():                                          # resume: images already probed are skipped
        done = {json.loads(l)["stem"] for l in jl.read_text().splitlines() if l.strip()}
    use_clef = not a.no_clef
    if use_clef and not clef.health():
        print("Clef-Flash is not healthy at :8097", file=sys.stderr); return 2
    with jl.open("a") as fh:
        for i, it in enumerate(items):
            if it["stem"] in done:
                continue
            rec = probe(it, use_clef, out / "crops")
            fh.write(json.dumps(rec) + "\n"); fh.flush()
            print(f"[{i + 1}/{len(items)}] {it['stem']}: {len(it['boxes'])} persons, {rec['wall_s']} s", flush=True)
    (out / "SUMMARY.md").write_text(summarise(out))
    print(f"wrote {out / 'SUMMARY.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
