"""Offline tests of pixel-to-ground geometry: hand-built poses first, then the real MuJoCo camera (no rendering)."""
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from patrol import geo, planner  # noqa: E402

W, H = 1280, 960
# camera 40 m up looking straight down; image right = world -y, image up = world +x (flying toward +x)
NADIR = {"pos": [0.0, 0.0, 40.0], "mat": [0.0, 1.0, 0.0, -1.0, 0.0, 0.0, 0.0, 0.0, 1.0], "fovy": 34.0}
F = (H / 2) / math.tan(math.radians(17.0))      # focal length in pixels for fovy 34 at H = 960


def look_pose(pos, target, fovy: float = 34.0) -> dict:
    """Hand-built pose looking from pos at target (not straight down), MuJoCo axes: x right, y up, looks along -z."""
    pos = np.asarray(pos, float)
    fwd = np.asarray(target, float) - pos
    fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, [0, 0, 1.0])
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    return {"pos": pos.tolist(), "mat": np.stack([right, up, -fwd], axis=1).flatten().tolist(), "fovy": fovy}


# ------------------------------------------------------------------ synthetic poses
def test_camera_pose_reads_only_the_camera_arrays_and_is_plain_json():
    stub = SimpleNamespace(cam={"inspect": 1},
                           data=SimpleNamespace(cam_xpos=np.array([[9.0, 9.0, 9.0], NADIR["pos"]]),
                                                cam_xmat=np.array([[9.0] * 9, NADIR["mat"]])),
                           model=SimpleNamespace(cam_fovy=np.array([60.0, 34.0])))
    pose = geo.camera_pose(stub, "inspect")
    assert pose == NADIR and json.loads(json.dumps(pose)) == pose
    assert all(type(x) is float for x in pose["pos"] + pose["mat"]) and type(pose["fovy"]) is float


def test_nadir_centre_is_the_point_below_and_the_axes_are_as_documented():
    assert geo.pixel_to_ground(W / 2, H / 2, W, H, NADIR) == pytest.approx((0.0, 0.0), abs=1e-9)
    right = geo.pixel_to_ground(W / 2 + 100, H / 2, W, H, NADIR)
    up = geo.pixel_to_ground(W / 2, H / 2 - 100, W, H, NADIR)
    assert right == pytest.approx((0.0, -40 * 100 / F), abs=1e-9)      # image right is world -y
    assert up == pytest.approx((40 * 100 / F, 0.0), abs=1e-9)          # image up is world +x
    assert geo.pixel_to_ground(W / 2, H / 2, W, H, NADIR, ground_z=10.0) == pytest.approx((0.0, 0.0), abs=1e-9)


def test_pixel_ray_is_a_unit_vector_from_the_camera():
    o, d = geo.pixel_ray(100, 700, W, H, look_pose((3, -4, 25), (30, 10, 0)))
    assert o.tolist() == [3.0, -4.0, 25.0] and np.linalg.norm(d) == pytest.approx(1.0)
    o, d = geo.pixel_ray(W / 2, H / 2, W, H, NADIR)
    assert d == pytest.approx([0.0, 0.0, -1.0], abs=1e-12)


@pytest.mark.parametrize("pose", [NADIR, look_pose((0, 0, 40), (30, 10, 0)), look_pose((-20, 5, 12), (0, 0, 0), 24.0)])
def test_round_trip_pixel_ground_pixel(pose):
    for u, v in [(0.5, 0.5), (640, 480), (100, 200), (1200, 900), (333.3, 777.7), (1279.5, 0.5)]:
        g = geo.pixel_to_ground(u, v, W, H, pose)
        assert g is not None
        assert geo.ground_to_pixel(g[0], g[1], W, H, pose) == pytest.approx((u, v), abs=1e-6)


def test_nadir_footprint_matches_the_planner_and_is_centred():
    poly = geo.frame_footprint(W, H, NADIR)
    sides = [math.dist(poly[i], poly[(i + 1) % 4]) for i in range(4)]
    along, cross = planner.footprint(40.0, 34.0, W / H)
    assert sorted(sides) == pytest.approx(sorted([along, cross, along, cross]), abs=1e-9)
    assert np.mean(poly, axis=0) == pytest.approx((0.0, 0.0), abs=1e-9)
    # corner order (0,0), (W,0), (W,H), (0,H): top-left is ahead (+x) and to the left (+y), bottom-right the opposite
    assert poly[0] == pytest.approx((along / 2, cross / 2)) and poly[2] == pytest.approx((-along / 2, -cross / 2))


def test_rays_above_the_horizon_return_none():
    level = look_pose((0, 0, 40), (100, 0, 40))                      # looking at the horizon
    assert geo.pixel_to_ground(W / 2, 10, W, H, level) is None        # sky
    assert geo.pixel_to_ground(W / 2, H / 2, W, H, level) is None     # exactly level
    g = geo.pixel_to_ground(W / 2, H - 1, W, H, level)                # below the horizon: far ahead on the ground
    assert g is not None and g[0] > 100 and abs(g[1]) < 1e-9
    assert geo.frame_footprint(W, H, level) is None
    assert geo.frame_footprint(W, H, look_pose((0, 0, 40), (60, 0, 0))) is not None   # 34 deg down: top edge below it


def test_a_grazing_ray_returns_none_instead_of_a_point_at_infinity():
    grazing = look_pose((0, 0, 40), (100, 0, 40 - 1e-10))             # centre ray 1e-12 below the horizontal
    assert geo.pixel_to_ground(W / 2, H / 2, W, H, grazing) is None
    assert geo.pixel_to_ground(W / 2, H / 2 + 50, W, H, grazing) is not None     # a real descent still lands


def test_a_ray_that_meets_the_plane_behind_the_camera_returns_none():
    assert geo.pixel_to_ground(W / 2, H / 2, W, H, look_pose((0, 0, 40), (50, 0, 80))) is None    # looking up
    assert geo.pixel_to_ground(W / 2, H / 2, W, H, NADIR, ground_z=60.0) is None                  # plane above us


def test_ground_to_pixel_returns_none_behind_or_outside():
    assert geo.ground_to_pixel(0, 0, W, H, NADIR) == pytest.approx((W / 2, H / 2))
    assert geo.ground_to_pixel(0, 0, W, H, NADIR, z=50.0) is None                  # above the camera: behind it
    assert geo.ground_to_pixel(100, 0, W, H, NADIR) is None                        # far outside the frame
    assert geo.ground_to_pixel(0, 100, W, H, NADIR) is None
    assert geo.ground_to_pixel(-30, 0, W, H, look_pose((0, 0, 10), (50, 0, 0))) is None   # behind a forward camera


def test_gsd():
    assert geo.gsd(40.0, H, 34.0) == pytest.approx(0.02548, abs=1e-5)
    assert geo.gsd(40.0, H, 34.0) == pytest.approx(planner.footprint(40.0)[0] / H)
    assert geo.gsd(20.0, H, 34.0) == pytest.approx(geo.gsd(40.0, H, 34.0) / 2)


# ------------------------------------------------------------------ the real simulator camera
@pytest.fixture(scope="module")
def sim():
    pytest.importorskip("mujoco")
    from patrol import world
    from patrol.sim import Sim
    s = Sim(world.search_spec(0, "snow", []), start=(5.0, -20.0, 40.0))
    yield s
    s.close()


def check_against_sim(sim, points, tol=0.02):
    """Project known ground points with the sim, send the pixels back through geo, and compare."""
    pose = geo.camera_pose(sim, "inspect")
    for p in points:
        proj = sim.project(p, "inspect", W, H)
        assert proj is not None, f"{p} is outside the frame"
        u, v, _ = proj
        assert geo.pixel_to_ground(u, v, W, H, pose, ground_z=p[2]) == pytest.approx(p[:2], abs=tol)
        assert geo.ground_to_pixel(p[0], p[1], W, H, pose, z=p[2]) == pytest.approx((u, v), abs=1e-6)
        o, d = geo.pixel_ray(u, v, W, H, pose)
        assert np.linalg.norm(np.cross(d, np.asarray(p) - o)) < 1e-6          # the ray passes through the point
    return pose


def test_sim_near_nadir_pixels_land_on_the_projected_ground_points(sim):
    sim.aim("inspect", (5.3, -20.0, 0.0))          # near-nadir, as the sweep does
    pose = check_against_sim(sim, [(5.0, -20.0, 0.0), (8.0, -25.0, 0.0), (-3.0, -10.0, 0.0), (14.0, -32.0, 0.0),
                                   (1.0, -8.0, 0.0), (8.0, -25.0, 1.5)])
    assert json.loads(json.dumps(pose)) == pose and type(pose["fovy"]) is float
    h = pose["pos"][2]
    assert h == pytest.approx(39.9, abs=0.01) and pose["fovy"] == pytest.approx(34.0)
    # the footprint of the real camera has the planner's size (a 0.4 degree tilt costs well under 1 %)
    poly = geo.frame_footprint(W, H, pose)
    sides = [math.dist(poly[i], poly[(i + 1) % 4]) for i in range(4)]
    along, cross = planner.footprint(h, 34.0, W / H)
    assert sorted(sides) == pytest.approx(sorted([along, cross, along, cross]), rel=0.01)
    assert np.mean(poly, axis=0) == pytest.approx((5.3, -20.0), abs=0.2)
    assert geo.gsd(h, H, pose["fovy"]) == pytest.approx(along / H)


def test_sim_oblique_pixels_land_on_the_projected_ground_points(sim):
    sim.aim("inspect", (35.0, -20.0, 0.0))         # looking 30 m ahead
    pose = check_against_sim(sim, [(35.0, -20.0, 0.0), (28.0, -26.0, 0.0), (45.0, -14.0, 0.0), (22.0, -20.0, 0.0),
                                   (50.0, -22.0, 0.0), (35.0, -20.0, 2.0)])
    poly = geo.frame_footprint(W, H, pose)
    assert poly is not None
    xs = [p[0] for p in poly]
    assert min(xs) == pytest.approx(5 + 39.9 * math.tan(math.radians(36.87 - 17)), abs=1.0)   # near edge, 19.9 deg
    assert max(xs) == pytest.approx(5 + 39.9 * math.tan(math.radians(36.87 + 17)), abs=1.5)   # far edge, 53.9 deg
    near, far = math.dist(poly[2], poly[3]), math.dist(poly[0], poly[1])
    assert far > 1.4 * near                         # a trapezoid: the far (top) edge spans more ground than the near
