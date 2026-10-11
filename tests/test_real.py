"""Offline tests of the real-imagery loader and probe geometry (no models; HERIDAL files are not needed)."""
import io
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from patrol import real  # noqa: E402
from tools import real_probe  # noqa: E402

VOC = """<annotation><object><name>person</name><bndbox><xmin>1888</xmin><xmax>1942</xmax><ymin>1836</ymin>
<ymax>1872</ymax></bndbox></object><size><width>4000</width><height>3000</height></size><object><name>person</name>
<bndbox><xmin>2802</xmin><xmax>2844</xmax><ymin>133</ymin><ymax>207</ymax></bndbox></object></annotation>"""


def test_split_halves_are_disjoint_and_cover_every_location():
    assert not real.TUNING & real.HELD_OUT
    assert real.split_of("test_BRA_0001") == "tuning" and real.split_of("test_SB_0007") == "held_out"
    with pytest.raises(KeyError):
        real.split_of("test_XYZ_0001")


def test_voc_boxes_and_images(tmp_path):
    (tmp_path / "test_BRS_0006.xml").write_text(VOC)
    Image.new("RGB", (8, 6)).save(tmp_path / "test_BRS_0006.jpg")
    Image.new("RGB", (8, 6)).save(tmp_path / "test_SB_0001.jpg")            # no annotation: skipped
    items = real.images(data=tmp_path)
    assert [i["stem"] for i in items] == ["test_BRS_0006"]
    assert items[0]["boxes"][0] == {"x0": 1888, "y0": 1836, "x1": 1942, "y1": 1872, "label": "person"}
    assert real.images("held_out", data=tmp_path) == []


def test_frames_cover_the_photo_and_map_back_to_native_pixels():
    a = np.zeros((3000, 4000, 3), np.uint8)
    fr = list(real_probe.frames(a))
    native = [f for f in fr if f[0] == "native"]
    assert len(native) == 16 and all(f[1].shape[:2] == (960, 1280) for f in native)
    assert max(f[3] for f in native) == 4000 - 1280 and max(f[4] for f in native) == 3000 - 960
    view, f, s, x, y = fr[-1]
    assert view == "down" and f.shape[:2] == (960, 1280) and s == pytest.approx(3.125)
    person = {"x0": 1888, "y0": 1836, "x1": 1942, "y1": 1872}
    assert real_probe.hit({"x0": 600, "y0": 585, "x1": 610, "y1": 595}, person, s, 0, 0)       # 1875-1906, 1828-1859
    assert not real_probe.hit({"x0": 0, "y0": 0, "x1": 10, "y1": 10}, person, s, 0, 0)
    assert real_probe.in_frame(person, f, s, 0, 0)


def test_closeup_is_framed_like_the_flight_zoom():
    a = np.zeros((3000, 4000, 3), np.uint8)
    im = Image.open(io.BytesIO(real_probe.closeup(a, 3990, 10)))           # clamped at the corner
    assert im.size == (real_probe.CFG.zoom_w, real_probe.CFG.zoom_h)
