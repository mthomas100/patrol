"""MuJoCo wrapper: a kinematic inspection drone (mocap body) with a pan-tilt gimbal camera.

The drone is kinematic on purpose: velocity commands are integrated with acceleration and speed limits, so runs are
exactly reproducible from a seed and the control code under test is the decision loop, not rotor dynamics.
"""
from __future__ import annotations

import io
import math
import os

os.environ.setdefault("MUJOCO_GL", "cgl")   # offscreen on macOS, no window

import mujoco
import numpy as np
from PIL import Image

from . import world


def _look_quat(yaw: float, pan: float, tilt: float) -> np.ndarray:
    """Quaternion for a MuJoCo camera (looks along its -z, y up) pointing at heading yaw+pan, tilted down by tilt."""
    a = yaw + pan
    v = np.array([math.cos(tilt) * math.cos(a), math.cos(tilt) * math.sin(a), -math.sin(tilt)])
    r = np.cross(v, [0, 0, 1.0]); r /= np.linalg.norm(r)
    u = np.cross(r, v)
    mat = np.stack([r, u, -v], axis=1).flatten()
    q = np.zeros(4); mujoco.mju_mat2Quat(q, mat)
    return q


class Sim:
    MAX_SPEED = 6.0     # m/s
    MAX_ACC = 3.0       # m/s^2

    def __init__(self, spec: dict, start=(-15.0, -12.0, 13.0)):
        self.spec = spec
        self.model = mujoco.MjModel.from_xml_string(world.build_mjcf(spec))
        self.data = mujoco.MjData(self.model)
        self.mocap = self.model.body("drone").mocapid[0]
        self.cam = {n: self.model.camera(n).id for n in ("wide", "inspect", "zoom", "chase", "map")}
        self.pos = np.array(start, dtype=float)
        self.vel = np.zeros(3)
        self.yaw = 0.0
        self.t = 0.0
        self.odometer = 0.0
        self.aims: dict[str, np.ndarray] = {}
        self.set_gimbal(pan=math.radians(55), tilt=math.radians(8))
        self._renderers: dict[tuple[int, int], mujoco.Renderer] = {}
        self._sync()

    # ------------------------------------------------------------ state
    def set_gimbal(self, pan: float, tilt: float, zoom_target=None):
        """Wide camera: fixed pan left of heading and tilt down. Optionally aim the zoom camera at a world point."""
        self.pan, self.tilt = pan, tilt
        self.model.cam_quat[self.cam["wide"]] = _look_quat(0.0, pan, tilt)
        for c in ("inspect", "zoom"):
            if c not in self.aims:
                self.model.cam_quat[self.cam[c]] = _look_quat(0.0, pan, tilt)
        if zoom_target is not None:
            self.aim("zoom", zoom_target)

    def aim(self, camera: str, target):
        """Point a gimbal camera (inspect or zoom) at a world point. Takes effect at the next _sync()/step()."""
        self.aims[camera] = np.asarray(target, float)
        self._sync()

    def _sync(self):
        self.data.mocap_pos[self.mocap] = self.pos
        q = np.zeros(4); mujoco.mju_euler2Quat(q, np.array([0, 0, self.yaw]), "xyz")
        self.data.mocap_quat[self.mocap] = q
        for cam, target in self.aims.items():    # gimbals stay locked on their targets as the drone moves
            d = target - self.pos
            a = math.atan2(d[1], d[0]) - self.yaw
            t = -math.atan2(d[2], math.hypot(d[0], d[1]))
            self.model.cam_quat[self.cam[cam]] = _look_quat(0.0, a, t)
        mujoco.mj_forward(self.model, self.data)

    def step(self, v_cmd, dt: float):
        """Advance sim time by dt toward the commanded world-frame velocity (m/s), within limits."""
        v_cmd = np.asarray(v_cmd, float)
        s = np.linalg.norm(v_cmd)
        if s > self.MAX_SPEED:
            v_cmd = v_cmd * self.MAX_SPEED / s
        sub = max(1, int(math.ceil(dt / 0.02)))
        h = dt / sub
        for _ in range(sub):
            dv = v_cmd - self.vel
            n = np.linalg.norm(dv)
            if n > self.MAX_ACC * h:
                dv *= self.MAX_ACC * h / n
            self.vel += dv
            self.pos += self.vel * h
            self.odometer += float(np.linalg.norm(self.vel)) * h
        self.t += dt
        self._sync()

    def telemetry(self) -> dict:
        return {"t": round(self.t, 2), "x": round(float(self.pos[0]), 2), "y": round(float(self.pos[1]), 2),
                "z": round(float(self.pos[2]), 2), "vx": round(float(self.vel[0]), 2),
                "speed": round(float(np.linalg.norm(self.vel)), 2), "odometer": round(self.odometer, 1)}

    # ------------------------------------------------------------ rendering
    def render(self, camera: str = "wide", width: int = 512, height: int = 384) -> np.ndarray:
        key = (height, width)
        if key not in self._renderers:
            self._renderers[key] = mujoco.Renderer(self.model, height, width)
        r = self._renderers[key]
        opt = mujoco.MjvOption()
        if camera in ("wide", "inspect", "zoom"):
            opt.geomgroup[3] = 0     # onboard cameras do not see the drone's own body
        r.update_scene(self.data, camera=self.cam[camera], scene_option=opt)
        return r.render()

    def jpeg(self, camera="wide", width=512, height=384, quality=85) -> bytes:
        buf = io.BytesIO()
        Image.fromarray(self.render(camera, width, height)).save(buf, "JPEG", quality=quality)
        return buf.getvalue()

    def project(self, point, camera="wide", width=512, height=384):
        """Pixel (u, v) and depth of a world point in a camera, or None if behind it or outside the frame."""
        i = self.cam[camera]
        R = self.data.cam_xmat[i].reshape(3, 3)
        d = R.T @ (np.asarray(point, float) - self.data.cam_xpos[i])   # camera frame: x right, y up, -z forward
        depth = -d[2]
        if depth <= 0.1:
            return None
        f = (height / 2) / math.tan(math.radians(self.model.cam_fovy[i]) / 2)
        u, v = width / 2 + f * d[0] / depth, height / 2 - f * d[1] / depth
        if not (0 <= u < width and 0 <= v < height):
            return None
        return float(u), float(v), float(depth)

    def visible_defects(self, camera="wide", width=512, height=384, max_depth=30.0) -> list[dict]:
        """Ground truth: planted defects inside this camera's frame and within max_depth metres."""
        out = []
        for d in self.spec["defects"]:
            p = self.project((d["x"], d["y"], d["z"]), camera, width, height)
            if p and p[2] <= max_depth:
                out.append({"id": d["id"], "type": d["type"], "u": round(p[0]), "v": round(p[1]),
                            "depth": round(p[2], 1)})
        return out

    def vegetation_clearance(self, camera: str = "zoom", width: int = 256, height: int = 192) -> float | None:
        """Rangefinder: depth + segmentation from a gimbal camera. Returns the smallest 3D distance (m) between any
        visible tree surface and any conductor, or None when no vegetation is in view. Code-owned sensing, the way
        corridor LiDAR measures clearance; no ground truth is read."""
        key = ("seg", height, width)
        if key not in self._renderers:
            self._renderers[key] = mujoco.Renderer(self.model, height, width)
        r = self._renderers[key]
        opt = mujoco.MjvOption(); opt.geomgroup[3] = 0
        r.update_scene(self.data, camera=self.cam[camera], scene_option=opt)
        r.enable_segmentation_rendering(); seg = r.render()[:, :, 0].copy(); r.disable_segmentation_rendering()
        r.enable_depth_rendering(); depth = r.render().copy(); r.disable_depth_rendering()
        if not hasattr(self, "_veg_ids"):
            self._veg_ids = np.array([i for i in range(self.model.ngeom)
                                      if (self.model.geom(i).name or "").startswith("veg_")])
        mask = np.isin(seg, self._veg_ids)
        if not mask.any():
            return None
        v, u = np.nonzero(mask)
        d = depth[v, u]
        i = self.cam[camera]
        f = (height / 2) / math.tan(math.radians(self.model.cam_fovy[i]) / 2)
        pc = np.stack([(u + 0.5 - width / 2) / f * d, -(v + 0.5 - height / 2) / f * d, -d], axis=1)  # camera frame
        R = self.data.cam_xmat[i].reshape(3, 3)
        pw = pc @ R.T + self.data.cam_xpos[i]
        sp = self.spec["spacing"]
        frac = np.clip((pw[:, 0] % sp) / sp, 0, 1)
        zc = world.conductor_z(frac, sp)
        best = min(float(np.min(np.hypot(pw[:, 1] - y, pw[:, 2] - zc))) for y in world.PHASES.values())
        return round(best, 2)

    def close(self):
        for r in self._renderers.values():
            r.close()
        self._renderers.clear()
