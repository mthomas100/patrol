"""Scene files: a test set up by hand (the builder page, or a text editor) instead of seeded placement.

A scene is JSON:
  {"name": "creek-two", "terrain": "snow", "seed": 3, "half": 80,
   "items": [{"name": "blue_backpack", "x": -30.5, "y": 12.0, "yaw": 90, "role": "hiker"},
             {"name": "blue_tarp", "x": 40, "y": -20, "role": "decoy"}]}
terrain is a world.TERRAINS name; seed sets the clutter and the map (trail, stream); half is the half-width of the
square search area, m; each item is a primitive (world.PRIMS) or a built item (assets/items/<name>), placed at x, y
(m east and north of the area centre) and yaw (degrees). role "hiker" marks the missing person's things (the answer
key), "decoy" anything else. The scene is ground truth: search.build_scene places it, scoring reads it, the decision
path never does.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import world

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "fixtures" / "scenes"
ROLES = {"hiker": "clue", "clue": "clue", "decoy": "decoy"}    # scene word -> the spec's role (score() reads "clue")
INSET = 3.0     # an item closer than this to the area edge is half outside every sweep lane


def available() -> list[str]:
    """Every item a scene may place: the primitives and the built items."""
    built = sorted(p.parents[1].name for p in (ROOT / "assets" / "items").glob("*/mujoco/mujoco.json"))
    return sorted(world.PRIMS) + built


def validate(sc: dict) -> dict:
    """The scene with defaults filled in (seed 0, half 80, yaw 0, role decoy); SystemExit naming the first fault."""
    def bad(msg):
        raise SystemExit(f"scene {sc.get('name', '?')}: {msg}")
    out = {"name": str(sc.get("name") or "scene"), "terrain": sc.get("terrain", "snow"),
           "seed": int(sc.get("seed", 0)), "half": float(sc.get("half", 80.0)), "items": []}
    if out["terrain"] not in world.TERRAINS:
        bad(f"terrain {out['terrain']!r} is not one of {sorted(world.TERRAINS)}")
    if not 20.0 <= out["half"] <= 400.0:
        bad(f"half {out['half']} m is outside 20-400 m")
    names = set(available())
    for k, it in enumerate(sc.get("items") or []):
        if it.get("name") not in names:
            bad(f"item {k} {it.get('name')!r} is not built (have: {', '.join(sorted(names))})")
        role = it.get("role", "decoy")
        if role not in ROLES:
            bad(f"item {k} role {role!r} is not hiker or decoy")
        x, y = float(it["x"]), float(it["y"])
        if max(abs(x), abs(y)) > out["half"] - INSET:
            bad(f"item {k} {it['name']} at ({x:g}, {y:g}) is not inside the area (|x|, |y| <= {out['half'] - INSET:g})")
        out["items"].append({"name": it["name"], "x": x, "y": y, "yaw": float(it.get("yaw", 0.0)) % 360,
                             "role": "hiker" if ROLES[role] == "clue" else "decoy"})
    if not out["items"]:
        bad("no items")
    return out


def load(path) -> dict:
    p = Path(path)
    if not p.exists() and (DIR / p).exists():
        p = DIR / p
    if not p.exists() and (DIR / f"{p}.json").exists():
        p = DIR / f"{p}.json"
    return validate(json.loads(p.read_text()))


def save(sc: dict, path=None) -> Path:
    sc = validate(sc)
    p = Path(path) if path else DIR / f"{sc['name']}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(sc, indent=1) + "\n")
    return p


def hiker_items(sc: dict) -> list[str]:
    return [it["name"] for it in sc["items"] if it["role"] == "hiker"]
