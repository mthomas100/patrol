"""Scene specs and their MJCF: a power-line corridor with planted defects and ground truth.

A scene spec is plain JSON-able data (so tests and reports can store it). `build_mjcf(spec)` turns it into a MuJoCo
model string. Coordinates: x runs along the corridor, y to the left of a drone flying +x, z up, metres.
The drone flies at y = -standoff, so the line is on its left; phase "near" is the one closest to the drone.
"""
from __future__ import annotations

import math
import random

PHASES = {"near": -4.5, "middle": 0.0, "far": 4.5}   # crossarm tip y per phase
ARM_Z = 14.0            # crossarm height
TOWER_TOP = 16.5
INS_LEN = 1.8           # insulator string length
DISC_R, DISC_GAP, N_DISCS = 0.26, 0.17, 9
SAG = 1.6
COND_R = 0.07

DEFECT_TYPES = {
    "broken_insulator": "insulator string with missing and cracked discs (sheds), one disc hanging askew",
    "frayed_conductor": "conductor with broken strands splayed out from the line",
    "vegetation": "tree crown grown up into or within a metre of a conductor",
    "foreign_object": "bird nest or debris lodged on a crossarm or tangled on a conductor",
}


def corridor_spec(seed: int = 0, length: float = 300.0, spacing: float = 50.0,
                  defects: list[dict] | None = None, distractors: bool = True) -> dict:
    """A seeded corridor. `defects` entries: {"type", "at": pylon index or span index, "phase"}.
    Positions are derived here so the ground truth lives in one place."""
    rng = random.Random(seed)
    n = int(length // spacing) + 1
    pylons = [{"i": i, "x": i * spacing} for i in range(n)]
    if defects is None:
        defects = [{"type": "broken_insulator", "at": 2, "phase": "near"}]
    out = []
    for k, d in enumerate(defects):
        d = dict(d)
        d.setdefault("phase", "near")
        y = PHASES[d["phase"]]
        if d["type"] in ("broken_insulator",):
            x = pylons[d["at"]]["x"]
            z = ARM_Z - INS_LEN / 2
        elif d["type"] == "foreign_object" and d.get("where", "arm") == "arm":
            x = pylons[d["at"]]["x"]
            z = ARM_Z + 0.4
        else:  # on a span: at = span index, frac along it
            frac = d.get("frac", rng.uniform(0.35, 0.65))
            d["frac"] = round(frac, 3)
            x = (d["at"] + frac) * spacing
            z = conductor_z(frac, spacing)
        d.update(id=f"D{k + 1}", x=round(x, 2), y=y, z=round(z, 2), description=DEFECT_TYPES[d["type"]])
        out.append(d)
    trees = []
    if distractors:  # healthy trees well clear of the conductors (false-alarm bait)
        for s in range(n - 1):
            for _ in range(2):
                trees.append({"x": round((s + rng.uniform(0.1, 0.9)) * spacing, 2),
                              "y": round(rng.choice([-1, 1]) * rng.uniform(13, 22), 2),
                              "h": round(rng.uniform(5, 9), 2)})
    return {"kind": "corridor", "seed": seed, "length": length, "spacing": spacing,
            "pylons": pylons, "defects": out, "trees": trees}


def m2_spec(seed: int = 0, length: float = 300.0) -> dict:
    """M2 corridor: one defect of each type plus a second insulator, spread along 300 m, on the near phase."""
    return corridor_spec(seed, length=length, defects=[
        {"type": "vegetation", "at": 0},                       # mid span 0
        {"type": "broken_insulator", "at": 2},                 # tower 2 (x=100)
        {"type": "frayed_conductor", "at": 2},                 # mid span 2
        {"type": "foreign_object", "at": 4, "where": "arm"},   # bird nest on tower 4 crossarm (x=200)
        {"type": "foreign_object", "at": 4, "where": "span"},  # debris hanging on span 4
        {"type": "broken_insulator", "at": 5},                 # tower 5 (x=250)
    ])


def conductor_z(frac: float, spacing: float) -> float:
    """Height of a conductor at fraction `frac` along a span (parabolic sag)."""
    return ARM_Z - INS_LEN - SAG * 4 * frac * (1 - frac)


# ---------------------------------------------------------------- MJCF
def _g(kind, pos=None, size=None, rgba=None, fromto=None, euler=None, mat=None, name=None):
    a = [f'type="{kind}"']
    if name:
        a.append(f'name="{name}"')
    if fromto is not None:
        a.append('fromto="%s"' % " ".join(f"{v:.3f}" for v in fromto))
    if pos is not None:
        a.append('pos="%s"' % " ".join(f"{v:.3f}" for v in pos))
    if size is not None:
        a.append('size="%s"' % " ".join(f"{v:.3f}" for v in size))
    if euler is not None:
        a.append('euler="%s"' % " ".join(f"{v:.2f}" for v in euler))
    if mat:
        a.append(f'material="{mat}"')
    elif rgba:
        a.append('rgba="%s"' % " ".join(f"{v:.2f}" for v in rgba))
    return "<geom %s/>" % " ".join(a)


def _tower(x):
    g = []
    w0, w1 = 2.2, 0.7   # half-width at base and top
    for sx in (-1, 1):
        for sy in (-1, 1):
            g.append(_g("capsule", fromto=(x + sx * w0, sy * w0, 0, x + sx * w1, sy * w1, TOWER_TOP), size=(0.12,),
                        mat="steel"))
    # cross bracing on the two faces seen from the side
    levels = [0, 3.5, 7, 10.5, TOWER_TOP - 2.5]
    for a, b in zip(levels, levels[1:]):
        wa = w0 + (w1 - w0) * a / TOWER_TOP
        wb = w0 + (w1 - w0) * b / TOWER_TOP
        for sy in (-1, 1):
            g.append(_g("capsule", fromto=(x - wa, sy * wa, a, x + wb, sy * wb, b), size=(0.05,), mat="steel"))
            g.append(_g("capsule", fromto=(x + wa, sy * wa, a, x - wb, sy * wb, b), size=(0.05,), mat="steel"))
        for sx in (-1, 1):
            g.append(_g("capsule", fromto=(x + sx * wa, -wa, a, x + sx * wb, wb, b), size=(0.05,), mat="steel"))
    # crossarm
    g.append(_g("box", pos=(x, 0, ARM_Z + 0.15), size=(0.25, PHASES["far"] + 0.6, 0.15), mat="steel"))
    g.append(_g("capsule", fromto=(x, -0.7, TOWER_TOP, x, 0.7, TOWER_TOP), size=(0.1,), mat="steel"))
    return g


def _insulator(x, y, broken=False, rng=None):
    g = [_g("cylinder", fromto=(x, y, ARM_Z, x, y, ARM_Z - INS_LEN), size=(0.035,), rgba=(0.35, 0.35, 0.38, 1))]
    missing = {2, 3, 6} if broken else set()
    for k in range(N_DISCS):
        z = ARM_Z - 0.12 - k * DISC_GAP
        if k in missing:
            continue
        if broken and k == 4:   # cracked disc hanging askew, scorched
            g.append(_g("cylinder", pos=(x + 0.1, y, z - 0.05), size=(DISC_R, 0.035), euler=(35, 20, 0),
                        rgba=(0.12, 0.1, 0.08, 1)))
            continue
        g.append(_g("cylinder", pos=(x, y, z), size=(DISC_R, 0.035), mat="glass"))
    if broken:  # shards on the crossarm below the gap
        for s in range(4):
            g.append(_g("box", pos=(x + 0.3 * (s - 1.5), y + 0.15, ARM_Z - INS_LEN - 0.5 - 0.1 * s),
                        size=(0.08, 0.05, 0.02), euler=(s * 40, s * 25, 0), rgba=(0.15, 0.13, 0.1, 1)))
    return g


def _span(x0, spacing, y, segs=12):
    g = []
    for k in range(segs):
        f0, f1 = k / segs, (k + 1) / segs
        g.append(_g("capsule", fromto=(x0 + f0 * spacing, y, conductor_z(f0, spacing),
                                       x0 + f1 * spacing, y, conductor_z(f1, spacing)), size=(COND_R,), mat="cond"))
    return g


def _frayed(d, rng):
    g = []
    for s in range(9):
        ang = rng.uniform(0, 2 * math.pi)
        L = rng.uniform(0.6, 1.4)
        dx = rng.uniform(-0.4, 0.4)
        g.append(_g("capsule", fromto=(d["x"] + dx, d["y"], d["z"],
                                       d["x"] + dx + rng.uniform(-0.5, 0.5), d["y"] + L * math.cos(ang),
                                       d["z"] + L * math.sin(ang)), size=(0.018,), rgba=(0.75, 0.55, 0.3, 1)))
    # a burnt patch on the conductor
    g.append(_g("capsule", fromto=(d["x"] - 0.5, d["y"], d["z"], d["x"] + 0.5, d["y"], d["z"]), size=(COND_R * 1.6,),
                rgba=(0.1, 0.08, 0.06, 1)))
    return g


_VEG = [0]


def _tree(x, y, h, rng, touching_z=None):
    """Tree geoms are named veg_* so the rangefinder can tell vegetation from steel and wire."""
    g = [_g("capsule", fromto=(x, y, 0, x, y, h * 0.55), size=(0.25,), rgba=(0.35, 0.24, 0.15, 1))]
    top = touching_z if touching_z is not None else h
    crown_r = 2.2 if touching_z is not None else max(1.5, h * 0.28)
    cz = top - crown_r * 0.6
    if touching_z is not None:
        g[0] = _g("capsule", fromto=(x, y, 0, x, y, cz), size=(0.3,), rgba=(0.35, 0.24, 0.15, 1))
    for k in range(5):
        _VEG[0] += 1
        g.append(_g("ellipsoid", pos=(x + rng.uniform(-0.8, 0.8), y + rng.uniform(-0.8, 0.8), cz + rng.uniform(-0.6, 0.6)),
                    size=(crown_r, crown_r * 0.9, crown_r * 0.8), rgba=(0.13 + 0.05 * k / 5, 0.38, 0.12, 1),
                    name=f"veg_{_VEG[0]}"))
    return g


def _foreign(d):
    x, y, z = d["x"], d["y"], d["z"]
    if d.get("where", "arm") == "arm":   # bird nest of sticks on the crossarm, near the phase
        g = [_g("ellipsoid", pos=(x, y + 0.6, z + 0.15), size=(0.7, 0.6, 0.35), rgba=(0.42, 0.3, 0.16, 1))]
        for s in range(8):
            a = s * math.pi / 4
            g.append(_g("capsule", fromto=(x + 0.8 * math.cos(a), y + 0.6 + 0.8 * math.sin(a), z,
                                           x - 0.6 * math.cos(a), y + 0.6 - 0.5 * math.sin(a), z + 0.45),
                        size=(0.03,), rgba=(0.3, 0.2, 0.1, 1)))
        return g
    # debris (a torn orange kite / plastic sheet) hanging from a conductor
    return [_g("box", pos=(x, y, z - 0.7), size=(0.6, 0.02, 0.7), euler=(0, 15, 0), rgba=(0.95, 0.4, 0.05, 1)),
            _g("capsule", fromto=(x, y, z, x + 0.3, y, z - 1.8), size=(0.015,), rgba=(0.9, 0.9, 0.9, 1))]


DRONE_XML = """    <body name="drone" mocap="true" pos="{x:.1f} {y:.1f} {z:.1f}">
      <geom type="box" size="0.35 0.35 0.1" rgba="0.92 0.92 0.95 1" contype="0" conaffinity="0" group="3"/>
      <geom type="capsule" fromto="-0.6 -0.6 0.05 0.6 0.6 0.05" size="0.05" rgba="0.2 0.2 0.22 1" contype="0" conaffinity="0" group="3"/>
      <geom type="capsule" fromto="-0.6 0.6 0.05 0.6 -0.6 0.05" size="0.05" rgba="0.2 0.2 0.22 1" contype="0" conaffinity="0" group="3"/>
      <geom type="cylinder" pos="0.6 0.6 0.12" size="0.32 0.015" rgba="1.0 0.45 0.05 0.85" contype="0" conaffinity="0" group="3"/>
      <geom type="cylinder" pos="0.6 -0.6 0.12" size="0.32 0.015" rgba="1.0 0.45 0.05 0.85" contype="0" conaffinity="0" group="3"/>
      <geom type="cylinder" pos="-0.6 0.6 0.12" size="0.32 0.015" rgba="0.15 0.15 0.15 0.85" contype="0" conaffinity="0" group="3"/>
      <geom type="cylinder" pos="-0.6 -0.6 0.12" size="0.32 0.015" rgba="0.15 0.15 0.15 0.85" contype="0" conaffinity="0" group="3"/>
      <geom type="sphere" pos="0.3 0 -0.15" size="0.12" rgba="0.1 0.1 0.12 1" contype="0" conaffinity="0" group="3"/>
      <body name="gimbal">
        <camera name="wide" pos="0 0 -0.1" fovy="62" mode="fixed" xyaxes="0 -1 0 0 0 1"/>
        <camera name="inspect" pos="0 0 -0.1" fovy="34" mode="fixed" xyaxes="0 -1 0 0 0 1"/>
        <camera name="zoom" pos="0 0 -0.1" fovy="24" mode="fixed" xyaxes="0 -1 0 0 0 1"/>
      </body>
    </body>
    <camera name="chase" pos="-25 -20 18" fovy="55"/>
"""


def build_mjcf(spec: dict) -> str:
    if spec["kind"] == "search":
        return build_search_mjcf(spec)
    _VEG[0] = 0
    drone = DRONE_XML.format(x=-15, y=-12, z=13)
    rng = random.Random(spec["seed"] * 7919 + 1)
    sp = spec["spacing"]
    defects_at_pylon = {(d["at"], d["phase"]) for d in spec["defects"] if d["type"] == "broken_insulator"}
    world = []
    for p in spec["pylons"]:
        world += _tower(p["x"])
        for ph, y in PHASES.items():
            world += _insulator(p["x"], y, broken=(p["i"], ph) in defects_at_pylon, rng=rng)
    for p in spec["pylons"][:-1]:
        for y in PHASES.values():
            world += _span(p["x"], sp, y)
    for t in spec["trees"]:
        world += _tree(t["x"], t["y"], t["h"], rng)
    for d in spec["defects"]:
        if d["type"] == "frayed_conductor":
            world += _frayed(d, rng)
        elif d["type"] == "vegetation":
            world += _tree(d["x"], d["y"] + 2.4, 0, rng, touching_z=d["z"] + 0.8)   # behind the near conductor
        elif d["type"] == "foreign_object":
            world += _foreign(d)
    L = spec["length"]
    body = "\n      ".join(world)
    return f"""<mujoco model="patrol-{spec['kind']}-{spec['seed']}">
  <visual>
    <global offwidth="1280" offheight="960" fovy="60"/>
    <quality shadowsize="4096"/>
    <headlight ambient="0.35 0.35 0.35" diffuse="0.45 0.45 0.45" specular="0.1 0.1 0.1"/>
    <map znear="0.0005" zfar="3" haze="0.3"/>
    <rgba haze="0.75 0.82 0.9 1"/>
  </visual>
  <asset>
    <texture type="skybox" builtin="gradient" rgb1="0.55 0.7 0.9" rgb2="0.9 0.93 0.97" width="512" height="512"/>
    <texture name="grass" type="2d" builtin="checker" rgb1="0.33 0.45 0.22" rgb2="0.36 0.48 0.24" mark="random"
             random="0.08" markrgb="0.45 0.52 0.3" width="512" height="512"/>
    <material name="grass" texture="grass" texrepeat="60 60" reflectance="0"/>
    <material name="steel" rgba="0.55 0.57 0.6 1" specular="0.3"/>
    <material name="glass" rgba="0.55 0.75 0.7 1" specular="0.6" shininess="0.8"/>
    <material name="cond" rgba="0.25 0.25 0.27 1" specular="0.5"/>
  </asset>
  <worldbody>
    <light directional="true" pos="0 0 50" dir="-0.3 0.4 -1" diffuse="0.75 0.72 0.65" castshadow="true"/>
    <geom type="plane" size="{L + 200:.0f} 200 0.1" pos="{L / 2:.1f} 0 0" material="grass"/>
{drone}
    <camera name="map" pos="{L / 2:.1f} -10 {L * 0.9:.0f}" xyaxes="1 0 0 0 1 0" fovy="60"/>
      {body}
  </worldbody>
</mujoco>
"""


def look_target(spec: dict, x: float, ahead: float = 9.0, phase: str = "near") -> tuple[float, float, float]:
    """Where code aims the inspection gimbal, from the corridor map alone (no ground truth): the near-phase
    insulator string of a tower coming up within [x-2, x+ahead+8], else the near conductor `ahead` metres on."""
    y = PHASES[phase]
    for p in spec["pylons"]:
        if x - 2 <= p["x"] <= x + ahead + 8:
            return (p["x"], y, ARM_Z - INS_LEN / 2)
    sp = spec["spacing"]
    xt = min(max(x + ahead, 0.0), spec["length"])
    frac = (xt % sp) / sp
    return (xt, y, conductor_z(frac, sp))


def describe_target(spec: dict, target, phase: str = "near") -> str:
    """Words for what the gimbal is aimed at, from the map (for the LLM prompt and the report)."""
    for p in spec["pylons"]:
        if abs(p["x"] - target[0]) < 0.5:
            return f"{phase}-phase insulator string and crossarm of tower {p['i']}"
    i = int(target[0] // spec["spacing"])
    return f"{phase}-phase conductor between towers {i} and {i + 1}"


# ---------------------------------------------------------------- Direction 2: open-terrain search scenes
TERRAINS = {   # ground texture colours (MuJoCo builtin checker, low contrast, random marks) and clutter style
    "snow": {"rgb1": "0.78 0.80 0.85", "rgb2": "0.78 0.80 0.85", "mark": "0.70 0.73 0.80", "trees": "conifer"},
    "grass": {"rgb1": "0.34 0.46 0.23", "rgb2": "0.34 0.46 0.23", "mark": "0.42 0.50 0.28", "trees": "broadleaf"},
}


def search_spec(seed: int = 0, terrain: str = "snow", items: list[dict] | None = None, size: float = 200.0,
                n_rocks: int = 60, n_trees: int = 40) -> dict:
    """An open search area centred on the origin. items: [{"name", "obj", "texture", "x", "y", "yaw", "role"}]
    with role "clue" or "decoy"; mesh paths come from patrol.items. Rocks and trees are seeded clutter. The item
    positions are ground truth: for placement and scoring only, never for the decision path."""
    rng = random.Random(seed * 31 + 7)
    h = size / 2
    rocks = [{"x": round(rng.uniform(-h, h), 1), "y": round(rng.uniform(-h, h), 1),
              "r": round(rng.uniform(0.3, 1.2), 2), "flat": round(rng.uniform(0.4, 0.8), 2)} for _ in range(n_rocks)]
    trees = [{"x": round(rng.uniform(-h, h), 1), "y": round(rng.uniform(-h, h), 1),
              "h": round(rng.uniform(5, 12), 1)} for _ in range(n_trees)]
    for it in items or []:   # keep clutter off the items so S0 measures the item, not an occlusion
        rocks = [r for r in rocks if math.hypot(r["x"] - it["x"], r["y"] - it["y"]) > 4]
        trees = [t for t in trees if math.hypot(t["x"] - it["x"], t["y"] - it["y"]) > 8]
    return {"kind": "search", "seed": seed, "terrain": terrain, "size": size, "length": size,
            "items": items or [], "rocks": rocks, "trees": trees, "defects": []}


def _search_tree(t, style, k):
    x, y, h = t["x"], t["y"], t["h"]
    if style == "conifer":
        g = [_g("capsule", fromto=(x, y, 0, x, y, h * 0.3), size=(0.2,), rgba=(0.3, 0.22, 0.15, 1))]
        for j in range(3):
            z = h * (0.3 + 0.22 * j)
            g.append(_g("ellipsoid", pos=(x, y, z + h * 0.1), size=(h * (0.22 - 0.05 * j),) * 2 + (h * 0.16,),
                        rgba=(0.12, 0.25 + 0.03 * j, 0.15, 1)))
        return g
    return [_g("capsule", fromto=(x, y, 0, x, y, h * 0.55), size=(0.25,), rgba=(0.35, 0.24, 0.15, 1)),
            _g("ellipsoid", pos=(x, y, h * 0.75), size=(h * 0.3, h * 0.28, h * 0.25), rgba=(0.15, 0.38, 0.12, 1))]


def _stones_along(points, step=0.32):
    """Small stones every `step` metres along a polyline (the SOS letters)."""
    out = []
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        out += [(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n) for k in range(n)]
    return out + [points[-1]]


def _arc(cx, cy, r, a0, a1, n=24):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)), cy + r * math.sin(math.radians(a0 + (a1 - a0) * k / n)))
            for k in range(n + 1)]


def _sos():
    s_pts = _arc(0, 0.5, 0.5, 20, 270) + _arc(0, -0.5, 0.5, 90, -160)
    o_pts = [(0.6 * math.cos(math.radians(a)), 1.0 * math.sin(math.radians(a))) for a in range(0, 361, 15)]
    stone = (0.16, 0.13, 0.08, (0.63, 0.61, 0.58, 1))
    out = []
    for dx, pts in ((-1.7, s_pts), (0.0, o_pts), (1.7, s_pts)):
        out += [(x + dx, y) + stone for x, y in _stones_along(pts)]
    return out


# items made of MuJoCo primitives (rocks need no mesh model): name -> [(dx, dy, sx, sy, sz, rgba)], plus real size
PRIMS = {
    "red_rock": ([(0.0, 0.0, 0.45, 0.35, 0.25, (0.55, 0.24, 0.17, 1))], 0.9),
    "grey_boulder": ([(0.0, 0.0, 0.7, 0.55, 0.45, (0.50, 0.50, 0.52, 1))], 1.4),
    "sos_rocks": (_sos(), 5.0),
}


def prim_geoms(it: dict, n: str) -> list[str]:
    yaw = math.radians(it.get("yaw", 0.0))
    c, s = math.cos(yaw), math.sin(yaw)
    return [_g("ellipsoid", pos=(it["x"] + c * dx - s * dy, it["y"] + s * dx + c * dy, sz * 0.5), size=(sx, sy, sz),
               rgba=rgba, euler=(0, 0, it.get("yaw", 0.0)), name=f"{n}_{j}")
            for j, (dx, dy, sx, sy, sz, rgba) in enumerate(PRIMS[it["prim"]][0])]


def build_search_mjcf(spec: dict) -> str:
    T = TERRAINS[spec["terrain"]]
    S = spec["size"]
    assets, world = [], []
    for r in spec["rocks"]:
        world.append(_g("ellipsoid", pos=(r["x"], r["y"], r["r"] * r["flat"] * 0.5),
                        size=(r["r"], r["r"] * 0.8, r["r"] * r["flat"]), rgba=(0.45, 0.44, 0.42, 1)))
    for k, t in enumerate(spec["trees"]):
        world += _search_tree(t, T["trees"], k)
    for i, it in enumerate(spec["items"]):
        n = f"item{i}"
        if it.get("prim"):
            world += prim_geoms(it, n)
            continue
        assets.append(f'<texture name="{n}_tex" type="2d" file="{it["texture"]}"/>')
        assets.append(f'<material name="{n}_mat" texture="{n}_tex" specular="0.2"/>')
        assets.append(f'<mesh name="{n}_mesh" file="{it["obj"]}"/>')
        world.append(f'<geom name="{n}" type="mesh" mesh="{n}_mesh" material="{n}_mat" '
                     f'pos="{it["x"]:.2f} {it["y"]:.2f} {it.get("z", 0.0):.3f}" euler="0 0 {it.get("yaw", 0):.1f}" '
                     'contype="0" conaffinity="0"/>')
    body = "\n      ".join(world)
    a = "\n    ".join(assets)
    return f"""<mujoco model="patrol-search-{spec['terrain']}-{spec['seed']}">
  <compiler angle="degree"/>
  <visual>
    <global offwidth="1280" offheight="960" fovy="60"/>
    <quality shadowsize="4096"/>
    <headlight ambient="0.35 0.35 0.35" diffuse="0.45 0.45 0.45" specular="0.1 0.1 0.1"/>
    <map znear="0.001" zfar="3" haze="0.2"/>
    <rgba haze="0.8 0.85 0.9 1"/>
  </visual>
  <asset>
    <texture type="skybox" builtin="gradient" rgb1="0.55 0.7 0.9" rgb2="0.9 0.93 0.97" width="512" height="512"/>
    <texture name="ground" type="2d" builtin="checker" rgb1="{T['rgb1']}" rgb2="{T['rgb2']}" mark="random"
             random="0.06" markrgb="{T['mark']}" width="512" height="512"/>
    <material name="ground" texture="ground" texrepeat="{S / 4:.0f} {S / 4:.0f}" reflectance="0"/>
    {a}
  </asset>
  <worldbody>
    <light directional="true" pos="0 0 80" dir="-0.3 0.4 -1" diffuse="0.75 0.72 0.65" castshadow="true"/>
    <geom type="plane" size="{S:.0f} {S:.0f} 0.1" material="ground"/>
    {DRONE_XML.format(x=0, y=-S / 2, z=40)}
    <camera name="map" pos="0 0 {S * 1.2:.0f}" xyaxes="1 0 0 0 1 0" fovy="60"/>
      {body}
  </worldbody>
</mujoco>
"""
