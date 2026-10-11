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


def _tree(x, y, h, rng, touching_z=None):
    g = [_g("capsule", fromto=(x, y, 0, x, y, h * 0.55), size=(0.25,), rgba=(0.35, 0.24, 0.15, 1))]
    top = touching_z if touching_z is not None else h
    crown_r = 2.2 if touching_z is not None else max(1.5, h * 0.28)
    cz = top - crown_r * 0.6
    if touching_z is not None:
        g[0] = _g("capsule", fromto=(x, y, 0, x, y, cz), size=(0.3,), rgba=(0.35, 0.24, 0.15, 1))
    for k in range(5):
        g.append(_g("ellipsoid", pos=(x + rng.uniform(-0.8, 0.8), y + rng.uniform(-0.8, 0.8), cz + rng.uniform(-0.6, 0.6)),
                    size=(crown_r, crown_r * 0.9, crown_r * 0.8), rgba=(0.13 + 0.05 * k / 5, 0.38, 0.12, 1)))
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


def build_mjcf(spec: dict) -> str:
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
    <body name="drone" mocap="true" pos="-15 -12 13">
      <geom type="box" size="0.25 0.25 0.06" rgba="0.15 0.15 0.18 1" contype="0" conaffinity="0" group="3"/>
      <geom type="cylinder" pos="0.3 0.3 0.08" size="0.18 0.01" rgba="0.8 0.2 0.1 0.6" contype="0" conaffinity="0" group="3"/>
      <geom type="cylinder" pos="0.3 -0.3 0.08" size="0.18 0.01" rgba="0.8 0.2 0.1 0.6" contype="0" conaffinity="0" group="3"/>
      <geom type="cylinder" pos="-0.3 0.3 0.08" size="0.18 0.01" rgba="0.2 0.2 0.2 0.6" contype="0" conaffinity="0" group="3"/>
      <geom type="cylinder" pos="-0.3 -0.3 0.08" size="0.18 0.01" rgba="0.2 0.2 0.2 0.6" contype="0" conaffinity="0" group="3"/>
      <body name="gimbal">
        <camera name="wide" pos="0 0 -0.1" fovy="62" mode="fixed" xyaxes="0 -1 0 0 0 1"/>
        <camera name="inspect" pos="0 0 -0.1" fovy="34" mode="fixed" xyaxes="0 -1 0 0 0 1"/>
        <camera name="zoom" pos="0 0 -0.1" fovy="16" mode="fixed" xyaxes="0 -1 0 0 0 1"/>
      </body>
    </body>
    <camera name="chase" mode="trackcom" pos="-14 -22 22" xyaxes="0.8 -0.6 0 0.3 0.4 0.87" target="drone"/>
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
