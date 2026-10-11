"""Sweep planner: how high to fly, which lanes to fly over a search area, and how much ground has been seen.

Conventions: the search area is a convex polygon [(x, y), ...] in world metres (either winding). Lanes run along x
(east-west) and are stacked along y. The sweep camera looks straight down with its image vertical axis along the
direction of flight, so the cross-track ground width is the image's horizontal extent:
    along = 2 h tan(vfov/2),  cross = along * aspect.
Lane spacing is the cross width less the overlap, so neighbouring frames share a strip and nothing falls in a gap.
Sweep height comes from the smallest clue: it keeps that clue as many pixels across as the reference item had at the
reference height, where the anomaly finder was measured to find it. Coverage is a grid of ground cells that frame
footprints (from patrol.geo) fill in, so the mission can say what fraction of the area it has actually looked at.
"""
from __future__ import annotations

import math

import numpy as np


def footprint(h: float, vfov_deg: float = 34.0, aspect: float = 4 / 3) -> tuple[float, float]:
    """Ground size (along, cross) in metres of a nadir frame from height h."""
    along = 2 * h * math.tan(math.radians(vfov_deg) / 2)
    return along, along * aspect


def lane_spacing(h: float, vfov_deg: float = 34.0, aspect: float = 4 / 3, overlap: float = 0.2) -> float:
    return footprint(h, vfov_deg, aspect)[1] * (1 - overlap)


def sweep_height(clue_sizes_m: list[float], ref_size: float = 0.55, ref_height: float = 40.0,
                 lo: float = 20.0, hi: float = 40.0) -> float:
    """Highest height at which the smallest clue is still as many pixels across as the reference item at ref_height."""
    if not clue_sizes_m:
        return hi
    return max(lo, min(hi, ref_height * (min(clue_sizes_m) / ref_size)))


def _x_extent(pts: list[tuple[float, float]], y: float) -> tuple[float, float] | None:
    """x range of a convex polygon along the line y = const."""
    xs = []
    for (ax, ay), (bx, by) in zip(pts, pts[1:] + pts[:1]):
        if min(ay, by) <= y <= max(ay, by):
            xs += [ax, bx] if ay == by else [ax + (y - ay) / (by - ay) * (bx - ax)]
    return (min(xs), max(xs)) if xs else None


def lanes(area, spacing: float) -> list[dict]:
    """Boustrophedon lanes: {"i", "y", "x0", "x1"} with x0 -> x1 the flying direction; lane 0 flies toward +x.
    ceil(depth / spacing) lanes are spread evenly over the area's depth, so the real spacing is at most `spacing`
    and the last band reaches the far edge (a fixed step left the northern strip unsearched); a narrower area gets
    one centred lane."""
    if spacing <= 0:
        raise ValueError("spacing must be positive")
    pts = [(float(x), float(y)) for x, y in area]
    ymin, ymax = min(p[1] for p in pts), max(p[1] for p in pts)
    n = max(1, math.ceil((ymax - ymin) / spacing - 1e-9))
    step = (ymax - ymin) / n
    ys = [ymin + step / 2 + k * step for k in range(n)]
    out = []
    for y in ys or [(ymin + ymax) / 2]:
        ext = _x_extent(pts, y)
        if ext is None:
            continue
        east = len(out) % 2 == 0
        out.append({"i": len(out), "y": y, "x0": ext[0] if east else ext[1], "x1": ext[1] if east else ext[0]})
    return out


def lanes_length(lanes: list[dict]) -> float:
    return float(sum(abs(ln["x1"] - ln["x0"]) for ln in lanes))


def _inside(px: np.ndarray, py: np.ndarray, poly) -> np.ndarray:
    """Mask of points inside (or on) a convex polygon: every edge cross product has one sign, either winding."""
    P = np.asarray(poly, float)
    cr = np.array([(bx - ax) * (py - ay) - (by - ay) * (px - ax)
                   for (ax, ay), (bx, by) in zip(P, np.roll(P, -1, axis=0))])
    return np.all(cr >= 0, axis=0) | np.all(cr <= 0, axis=0)


class Coverage:
    """Ground cells (default 2 m) inside the area polygon; mark() fills cells whose centre is inside a convex
    polygon (a frame footprint)."""

    def __init__(self, area, cell: float = 2.0):
        if cell <= 0:
            raise ValueError("cell must be positive")
        a = np.asarray(area, float)
        self.cell = float(cell)
        self.x0, self.y0 = float(a[:, 0].min()), float(a[:, 1].min())
        self.nx = max(1, math.ceil((a[:, 0].max() - self.x0) / cell - 1e-9))
        self.ny = max(1, math.ceil((a[:, 1].max() - self.y0) / cell - 1e-9))
        # cell centres, shape (ny, nx): row 0 is the southern row
        self._gx, self._gy = np.meshgrid(self.x0 + (np.arange(self.nx) + 0.5) * cell,
                                         self.y0 + (np.arange(self.ny) + 0.5) * cell)
        self.inside = _inside(self._gx, self._gy, a)
        self.hit = np.zeros_like(self.inside)

    def mark(self, poly) -> int:
        """Cover the area's cells whose centre is inside the polygon; returns how many were newly covered.
        A missing polygon (a frame whose footprint is None) marks nothing."""
        if poly is None or len(poly) < 3:
            return 0
        new = _inside(self._gx, self._gy, poly) & self.inside & ~self.hit
        self.hit |= new
        return int(new.sum())

    def fraction(self) -> float:
        n = int(self.inside.sum())
        return float(self.hit.sum()) / n if n else 0.0

    def grid(self) -> dict:
        """Compact log form: rows of '0' (to do), '1' (covered), '.' (outside the area), southern row first."""
        code = np.where(self.inside, np.where(self.hit, ord("1"), ord("0")), ord(".")).astype(np.uint8)
        return {"x0": self.x0, "y0": self.y0, "cell": self.cell, "nx": self.nx, "ny": self.ny,
                "rows": [r.tobytes().decode("ascii") for r in code]}


def sectors(lanes: list[dict], length: float = 40.0) -> list[dict]:
    """Each lane cut into equal pieces of at most `length` m, in flying order. A sector's id is its row letter (lane,
    south first) and column number (west first) on a common grid, e.g. "C3"; h is the lane's band height. Sectors let
    the slow thinker reorder the sweep (search along the trail first) without breaking coverage."""
    if not lanes:
        return []
    xmin = min(min(ln["x0"], ln["x1"]) for ln in lanes)
    ys = sorted(ln["y"] for ln in lanes)
    h = ys[1] - ys[0] if len(ys) > 1 else length
    out = []
    for ln in lanes:
        row = chr(ord("A") + ys.index(ln["y"]))
        n = max(1, math.ceil(abs(ln["x1"] - ln["x0"]) / length - 1e-9))
        step = (ln["x1"] - ln["x0"]) / n
        for k in range(n):
            a, b = ln["x0"] + k * step, ln["x0"] + (k + 1) * step
            col = int(((a + b) / 2 - xmin) // length) + 1
            out.append({"id": f"{row}{col}", "lane": ln["i"], "y": ln["y"], "x0": round(a, 2), "x1": round(b, 2),
                        "h": round(h, 2)})
    return out
