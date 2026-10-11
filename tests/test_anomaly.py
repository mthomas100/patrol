"""Offline tests of the anomaly finder on synthetic frames (no MuJoCo, no models)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from patrol import anomaly  # noqa: E402


def frame(bg, seed=0):
    rng = np.random.default_rng(seed)
    a = np.clip(np.array(bg, float) + rng.normal(0, 6, (384, 512, 3)), 0, 255)
    # common clutter: many dark-green tree blobs and grey rocks
    for k in range(25):
        y, x = rng.integers(0, 370), rng.integers(0, 500)
        a[y:y + 12, x:x + 12] = (30, 70, 35) if k % 2 else (115, 112, 108)
    return a


def test_small_blue_item_is_a_top_candidate_on_snow_and_grass():
    for bg in ((232, 236, 242), (88, 118, 58)):
        a = frame(bg)
        a[200:206, 300:305] = (25, 60, 200)          # a 6x5 px blue patch: a backpack seen from high up
        c = anomaly.candidates(a.astype(np.uint8), k=3)
        assert c and any(anomaly.contains(x, 302, 203) for x in c), c


def test_crop_is_a_square_jpeg():
    a = frame((232, 236, 242)).astype(np.uint8)
    c = {"x0": 500, "y0": 370, "x1": 512, "y1": 384}
    j = anomaly.crop(a, c, size=128)
    from PIL import Image
    import io
    assert Image.open(io.BytesIO(j)).size == (128, 128)
