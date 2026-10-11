"""A/B the qwen38 inspection note with and without the healthy-component reference photo, on recorded flags.

usage: .venv/bin/python -m tools.note_probe OUT_DIR RUN_DIR [RUN_DIR ...]
For every flag in each run that matches a planted defect, it re-asks qwen38 for the note both ways and scores the
note's defect_type against the planted type.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from patrol import escalate, report  # noqa: E402


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    rows = []
    for run in map(Path, sys.argv[2:]):
        spec = json.loads((run / "scene.json").read_text())
        s = json.loads((run / "summary.json").read_text())
        ev = [json.loads(l) for l in (run / "mission.jsonl").read_text().splitlines()]
        flags = {e["id"]: e for e in ev if e["type"] == "flag"}
        photos = {e["photo"]: e for e in ev if e["type"] == "photo"}
        for did, f in report.match(spec, s["flags"]).items():
            d = next(x for x in spec["defects"] if x["id"] == did)
            fe = flags[f["id"]]
            jpgs = [(run / p).read_bytes() for p in fe.get("photos") or [fe["photo"]]]
            what = photos.get(fe["photo"], {}).get("what", "nearest line equipment")
            for ref in (False, True):
                n = escalate.write_note(jpgs if len(jpgs) > 1 else jpgs[0], fe["target"][0], what, fe["nouls"],
                                        clearance=fe.get("clearance_m"), reference=ref)
                r = {"run": run.name, "defect": did, "truth": d["type"], "reference": ref,
                     "said": n.get("defect_type"), "right": n.get("defect_type") == d["type"],
                     "severity": n.get("severity"), "note": (n.get("note") or n.get("error") or "")[:160],
                     "wall_s": n.get("wall_s")}
                rows.append(r)
                print(json.dumps(r), flush=True)
    (out / "notes.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    for ref in (False, True):
        rs = [r for r in rows if r["reference"] == ref]
        print(f"reference={ref}: defect type right {sum(r['right'] for r in rs)}/{len(rs)}")


if __name__ == "__main__":
    main()
