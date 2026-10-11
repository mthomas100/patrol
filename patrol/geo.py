"""Pixel to ground geometry from the camera pose alone: what a real drone knows from its GPS, IMU and gimbal.

Nothing here reads scene contents, geom names, segmentation or the spec. camera_pose is the only function that touches
the sim, and it copies three arrays into a plain dict that can be logged and replayed later; every other function takes
that dict.

Conventions (MuJoCo): the camera frame has x right, y up and looks along -z. `mat` holds the camera axes as columns in
world coordinates (row-major, 9 floats), so a world point is pos + mat @ camera_point. The world is z-up and the ground
is the plane z = ground_z. Pixels: u = W/2 + f x/depth, v = H/2 - f y/depth with depth = -z and
f = (H/2) / tan(fovy/2), so v grows downward. The pixel grid is continuous: the frame spans [0, W] x [0, H].
"""
from __future__ import annotations

import math

import numpy as np

EPS = 1e-9      # a ray flatter than this never reaches the ground; a point nearer than this is not in front


def camera_pose(sim, camera: str) -> dict:
    """Pose of a sim camera as of its last _sync()/step(): {"pos": [3], "mat": [9, row-major], "fovy": degrees}."""
    i = sim.cam[camera]
    return {"pos": sim.data.cam_xpos[i].tolist(), "mat": sim.data.cam_xmat[i].tolist(),
            "fovy": float(sim.model.cam_fovy[i])}


def _unpack(pose: dict) -> tuple[np.ndarray, np.ndarray, float]:
    return np.asarray(pose["pos"], float), np.asarray(pose["mat"], float).reshape(3, 3), float(pose["fovy"])


def _focal(H: float, fovy_deg: float) -> float:
    return (H / 2) / math.tan(math.radians(fovy_deg) / 2)


def pixel_ray(u, v, W, H, pose: dict) -> tuple[np.ndarray, np.ndarray]:
    """World-frame ray through pixel (u, v): the camera position and a unit direction."""
    pos, R, fovy = _unpack(pose)
    f = _focal(H, fovy)
    d = R @ np.array([(u - W / 2) / f, -(v - H / 2) / f, -1.0])
    return pos, d / np.linalg.norm(d)


def pixel_to_ground(u, v, W, H, pose: dict, ground_z: float = 0.0) -> tuple[float, float] | None:
    """World (x, y) where the ray through pixel (u, v) meets the plane z = ground_z; None if it never does in front."""
    o, d = pixel_ray(u, v, W, H, pose)
    if abs(d[2]) < EPS:
        return None
    t = (ground_z - o[2]) / d[2]
    if t <= EPS:
        return None
    p = o + t * d
    return float(p[0]), float(p[1])


def ground_to_pixel(x, y, W, H, pose: dict, z: float = 0.0) -> tuple[float, float] | None:
    """Pixel (u, v) of the world point (x, y, z); None if it is behind the camera or outside the frame."""
    pos, R, fovy = _unpack(pose)
    c = R.T @ (np.array([x, y, z], float) - pos)    # camera frame
    depth = -c[2]
    if depth <= EPS:
        return None
    f = _focal(H, fovy)
    u, v = W / 2 + f * c[0] / depth, H / 2 - f * c[1] / depth
    if not (0 <= u <= W and 0 <= v <= H):
        return None
    return float(u), float(v)


def frame_footprint(W, H, pose: dict, ground_z: float = 0.0) -> list[tuple[float, float]] | None:
    """Ground polygon of the four image corners, in order (0,0), (W,0), (W,H), (0,H); None if any corner misses."""
    pts = [pixel_to_ground(u, v, W, H, pose, ground_z) for u, v in ((0, 0), (W, 0), (W, H), (0, H))]
    return None if any(p is None for p in pts) else pts


def gsd(h: float, H: int, fovy_deg: float) -> float:
    """Ground sample distance, metres per pixel, for a camera looking straight down from height h."""
    return 2 * h * math.tan(math.radians(fovy_deg) / 2) / H
