"""S7: fetch only the HERIDAL test split (images + VOC boxes) out of the 8.3 GB Zenodo zip, with HTTP range requests.

HERIDAL (Bozic-Stulic et al., FESB Split), CC BY 3.0, Zenodo record 5662351 (keras-retinanet VOC copy, Aalto).
Attribution is required wherever its images are shown. Standard library only; members are written by basename into
a fresh directory (no paths from the archive are trusted), and a provenance.json records what was fetched.

usage: .venv/bin/python -I tools/fetch_heridal.py [--out assets/real/heridal] [--list] [--limit N]
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import io
import json
import time
import urllib.request
import zipfile
from pathlib import Path

URL = "https://zenodo.org/records/5662351/files/heridal_keras_retinanet_voc.zip?download=1"
RECORD = "https://zenodo.org/records/5662351"
SIZE = 8_311_735_812


class RangeFile(io.RawIOBase):
    """A read-only, seekable view of a remote file: each read is one HTTP Range request."""

    def __init__(self, url: str, size: int):
        self.url, self.size, self.pos, self.fetched = url, size, 0, 0

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = {0: off, 1: self.pos + off, 2: self.size + off}[whence]
        return self.pos

    def readinto(self, b):
        n = min(len(b), self.size - self.pos)
        if n <= 0:
            return 0
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{self.pos + n - 1}"})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = r.read()
                break
            except (OSError, http.client.HTTPException):    # IncompleteRead on a dropped connection
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)
        b[:len(data)] = data
        self.pos += len(data)
        self.fetched += len(data)
        return len(data)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "assets" / "real" / "heridal"))
    ap.add_argument("--list", action="store_true", help="only list the archive's test members")
    ap.add_argument("--limit", type=int, default=0, help="fetch at most N test images (0: all)")
    a = ap.parse_args(argv)
    rf = io.BufferedReader(RangeFile(URL, SIZE), buffer_size=1 << 20)
    z = zipfile.ZipFile(rf)
    names = z.namelist()
    test = sorted(n for n in names if "test" in Path(n).name.lower() and not n.startswith("__MACOSX")
                  and not Path(n).name.startswith("._") and n.lower().endswith((".jpg", ".jpeg", ".png", ".xml")))
    imgs = [n for n in test if not n.lower().endswith(".xml")]
    print(f"{len(names)} members; {len(imgs)} test images, {len(test) - len(imgs)} test annotations")
    if a.list:
        for n in test[:20]:
            print(" ", n)
        return 0
    if a.limit:
        keep = {Path(n).stem for n in imgs[:a.limit]}
        test = [n for n in test if Path(n).stem in keep]
    out = Path(a.out)
    (out / "data").mkdir(parents=True, exist_ok=True)
    got = []
    for n in test:
        dst = out / "data" / Path(n).name           # basename only: never trust archive paths
        if not dst.exists():
            dst.write_bytes(z.read(n))
        got.append({"member": n, "file": dst.name, "bytes": dst.stat().st_size,
                    "sha256": hashlib.sha256(dst.read_bytes()).hexdigest()[:16]})
    (out / "provenance.json").write_text(json.dumps({
        "dataset": "HERIDAL (keras-retinanet VOC copy)", "record": RECORD, "url": URL, "archive_bytes": SIZE,
        "licence": "CC BY 3.0 (Zenodo API: cc-by-3.0)",
        "attribution": "HERIDAL dataset, Bozic-Stulic, Marusic, Gotovac, FESB, University of Split (Zenodo 5662351)",
        "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": got}, indent=1))
    print(f"wrote {len(got)} files to {out}/data ({sum(g['bytes'] for g in got) / 1e6:.0f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
