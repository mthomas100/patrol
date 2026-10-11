"""Anomaly finder: proposes odd-looking spots in a camera frame, RGB pixels only (no depth, no segmentation, no
scene data), classical CV on CPU, no training.

Score = colour rarity: each pixel's colour is quantised, and a colour that covers little of the frame scores high
(-log of its share). A lost backpack on snow or grass is a small patch of a colour the frame has little of; snow,
grass, shadows and even many trees share a few common colours. Rare pixels are smoothed, grouped into connected
blobs, and the blobs ranked by summed rarity. Clef then judges one crop per candidate (it cannot localise; see
DECISIONS 11:50).
"""
from __future__ import annotations

import io

import numpy as np
from PIL import Image
from scipy import ndimage

LEVELS = 12            # quantisation levels per channel
MIN_PIX = 4            # smallest blob kept, pixels
RANK = "mean"          # "mean": mean rarity x log(1 + area); "sum": summed rarity (first version)


def _rgb(img) -> np.ndarray:
    if isinstance(img, (bytes, bytearray)):
        img = Image.open(io.BytesIO(img))
    if isinstance(img, Image.Image):
        img = np.asarray(img.convert("RGB"))
    return np.asarray(img)[..., :3]


def rarity(img) -> np.ndarray:
    a = _rgb(img).astype(np.int32)
    q = (a * LEVELS // 256)
    code = (q[..., 0] * LEVELS + q[..., 1]) * LEVELS + q[..., 2]
    hist = np.bincount(code.ravel(), minlength=LEVELS ** 3).astype(np.float64)
    share = hist / code.size
    return -np.log(share[code] + 1e-9)


def candidates(img, k: int = 3, pct: float = 99.0, min_rarity: float = 6.0, pad: int = 6) -> list[dict]:
    """Top-k candidate boxes {x0, y0, x1, y1, score, area, cx, cy} in pixel coordinates, best first."""
    r = rarity(img)
    r = ndimage.uniform_filter(r, size=3)
    thr = max(np.percentile(r, pct), min_rarity)
    mask = ndimage.binary_closing(r >= thr, iterations=2)
    lab, n = ndimage.label(mask)
    if n == 0:
        return []
    idx = np.arange(1, n + 1)
    area = ndimage.sum(np.ones_like(r), lab, idx)
    score = ndimage.sum(r, lab, idx)
    boxes = ndimage.find_objects(lab)
    H, W = r.shape
    # rank by how rare the blob's colours are on average, with a weak size bonus: a small, very rare patch (a lost item)
    # must beat a large, moderately rare one (a tree on snow); summed rarity ranked trees first (runs/s0-altitude-hires)
    rank = (score / np.maximum(area, 1)) * np.log1p(area) if RANK == "mean" else score
    out = []
    for i in np.argsort(-rank):
        if area[i] < MIN_PIX:
            continue
        sy, sx = boxes[i]
        out.append({"x0": max(0, sx.start - pad), "y0": max(0, sy.start - pad), "x1": min(W, sx.stop + pad),
                    "y1": min(H, sy.stop + pad), "score": round(float(score[i]), 1), "area": int(area[i]),
                    "cx": round((sx.start + sx.stop) / 2, 1), "cy": round((sy.start + sy.stop) / 2, 1)})
        if len(out) == k:
            break
    return out


def contains(c: dict, u: float, v: float, slack: int = 4) -> bool:
    return c["x0"] - slack <= u <= c["x1"] + slack and c["y0"] - slack <= v <= c["y1"] + slack


def crop(img, c: dict, size: int = 256, min_side: int = 48) -> bytes:
    """A square JPEG crop around a candidate (at least min_side px of the frame), resized for Clef."""
    a = _rgb(img)
    H, W = a.shape[:2]
    side = max(min_side, c["x1"] - c["x0"], c["y1"] - c["y0"]) * 2
    cx, cy = (c["x0"] + c["x1"]) / 2, (c["y0"] + c["y1"]) / 2
    x0, y0 = int(max(0, min(W - side, cx - side / 2))), int(max(0, min(H - side, cy - side / 2)))
    im = Image.fromarray(a[y0:y0 + int(side), x0:x0 + int(side)]).resize((size, size), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=90)
    return buf.getvalue()
