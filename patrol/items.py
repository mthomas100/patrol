"""Search items: m3d GLB -> real-sized OBJ + texture PNG for MuJoCo, with provenance.

usage: .venv/bin/python -m patrol.items convert assets/items/blue_backpack --size 0.55
The GLB is scaled so its largest dimension is `size` metres, rotated z-up, and dropped so it rests on z = 0.
`--up z` keeps the mesh's own z as up: hy3d builds a top-down concept (a bag photographed from above) standing up,
so its depth axis is the real height. `--max-height` then flattens an over-puffed mesh to a believable height.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def find_glb(d: Path) -> Path:
    for pat in ("*-game/*_LOD0.glb", "*.glb"):     # m3d --post game writes <name>-game/<name>_LOD0.glb
        c = sorted(d.glob(pat))
        if c:
            return c[-1]
    raise SystemExit(f"no GLB in {d}")


def convert(d: Path, size: float, up: str = "y", max_height: float | None = None) -> dict:
    import trimesh
    glb = find_glb(d)
    scene = trimesh.load(glb, force="scene")
    mesh = trimesh.util.concatenate([g for g in scene.dump() if isinstance(g, trimesh.Trimesh)])
    if up == "y":    # glTF is y-up; MuJoCo is z-up
        mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    ext = mesh.bounds[1] - mesh.bounds[0]
    mesh.apply_scale(size / float(ext.max()))
    h = float(mesh.bounds[1][2] - mesh.bounds[0][2])
    if max_height and h > max_height:
        mesh.apply_transform(np.diag([1.0, 1.0, max_height / h, 1.0]))
    lo, hi = mesh.bounds
    mesh.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
    out = d / "mujoco"; out.mkdir(exist_ok=True)
    tex = None
    mat = getattr(mesh.visual, "material", None)
    img = getattr(mat, "baseColorTexture", None) or getattr(mat, "image", None)
    if img is not None:
        tex = out / "texture.png"
        img.convert("RGB").save(tex)
    obj = out / "mesh.obj"
    obj.write_text(trimesh.exchange.obj.export_obj(mesh, include_texture=True, include_normals=True, return_texture=False))
    info = {"glb": glb.name, "obj": str(obj.resolve()), "texture": str(tex.resolve()) if tex else None,
            "size_m": size, "up": up, "max_height": max_height, "extent_m": [round(float(v), 3) for v in (mesh.bounds[1] - mesh.bounds[0])],
            "faces": int(len(mesh.faces)), "has_uv": getattr(mesh.visual, "uv", None) is not None}
    (out / "mujoco.json").write_text(json.dumps(info, indent=1))
    return info


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("convert"); c.add_argument("dir"); c.add_argument("--size", type=float, required=True)
    c.add_argument("--up", default="y", choices=["y", "z"])
    c.add_argument("--max-height", type=float, default=None)
    a = ap.parse_args(argv)
    print(json.dumps(convert(Path(a.dir), a.size, a.up, a.max_height)))


if __name__ == "__main__":
    main()
