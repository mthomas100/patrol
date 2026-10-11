"""Real aerial imagery (S7): the HERIDAL test split, its person boxes, the tuning / held-out split, and the person clue.

HERIDAL (Bozic-Stulic, Marusic, Gotovac, FESB, University of Split; Zenodo 5662351, CC BY 3.0, attribution required
wherever its images are shown): 4000x3000 photos from 40-65 m over Mediterranean scrub, about 2 cm/px, people
annotated as VOC boxes. No dataset annotates belongings from a drone, so real imagery tests the person clue.

The split is by location code (the three letters in test_<LOC>_<n>), so held-out images come from places the tuning
never saw. It was fixed on 2026-10-11 before any result on these images was looked at (DECISIONS 16:40).
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "assets" / "real" / "heridal"
DATA = ROOT / "data"
ATTRIBUTION = "HERIDAL dataset (Bozic-Stulic, Marusic, Gotovac, FESB Split), CC BY 3.0"
GSD_M = 0.02            # metres per pixel at native resolution (DATASETS.md: 40-65 m, about 2 cm/px)

TUNING = {"BRA", "BRS", "GRO", "CAP", "MOB", "ZRI"}          # about 48 images
HELD_OUT = {"BLI", "BRK", "CAB", "MED", "SB", "TRS"}         # about 51 images

# written like the clues.CATALOGUE entries: the family's words, the from-above description Clef is asked about, a size
PERSON = {"name": "person", "family": "a person", "size_m": 1.7,
          "words": "a person on the ground seen from above: a human figure standing, walking, sitting or lying, "
                   "with a head, arms and legs"}


def location(stem: str) -> str:
    return stem.split("_")[1]


def split_of(stem: str) -> str:
    loc = location(stem)
    if loc in TUNING:
        return "tuning"
    if loc in HELD_OUT:
        return "held_out"
    raise KeyError(f"{stem}: location {loc} is in neither half")


def boxes(xml_path: Path) -> list[dict]:
    """Person boxes {x0, y0, x1, y1} in native pixels from a VOC annotation."""
    out = []
    for o in ET.parse(xml_path).getroot().iter("object"):
        b = o.find("bndbox")
        x0, x1, y0, y1 = (int(float(b.findtext(k))) for k in ("xmin", "xmax", "ymin", "ymax"))
        out.append({"x0": x0, "y0": y0, "x1": x1, "y1": y1, "label": o.findtext("name")})
    return out


def images(split: str | None = None, data: Path = DATA) -> list[dict]:
    """[{stem, jpg, split, boxes}] for every image with an annotation, sorted, optionally one half only."""
    out = []
    for jpg in sorted(data.glob("test_*.jpg")):
        xml = jpg.with_suffix(".xml")
        if not xml.exists():
            continue
        s = split_of(jpg.stem)
        if split and s != split:
            continue
        out.append({"stem": jpg.stem, "jpg": jpg, "split": s, "boxes": boxes(xml)})
    return out
