"""Write runs/<dir>/REPORT.md from mission.jsonl + summary.json + scene.json.

usage: .venv/bin/python -m patrol.report RUN_DIR [--min-recall R] [--max-false-alarms N]
Exit code 0 when every check passes, 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path


def versions() -> dict:
    v = {"python": platform.python_version()}
    try:
        import mujoco
        v["mujoco"] = mujoco.__version__
    except Exception:
        pass
    v["clef"] = "clef-flash-mlx (mlx-community/clef-flash-8bit @ dfa0993, upstream Cloudflare/clef-flash @ 17f0b0a)"
    v["llm"] = "qwen38 via llama-swap :8090"
    try:
        v["git"] = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                                  cwd=Path(__file__).parent).stdout.strip()
    except Exception:
        pass
    return v


def match(spec: dict, flags: list[dict]) -> dict:
    """defect id -> the first flag within 8 m along the corridor and on the same phase (the summary's rule)."""
    found = {}
    for f in flags:
        for d in spec["defects"]:
            if abs(d["x"] - f["x"]) <= 8 and abs(d["y"] - f["y"]) < 2:
                found.setdefault(d["id"], f)
    return found


def build(run: Path, min_recall: float, max_false_alarms: int, require_notes: bool,
          min_clef_share: float = 0.0) -> tuple[str, bool, list]:
    s = json.loads((run / "summary.json").read_text())
    spec = json.loads((run / "scene.json").read_text())
    events = [json.loads(l) for l in (run / "mission.jsonl").read_text().splitlines()]
    flags = {e["id"]: e for e in events if e["type"] == "flag"}
    notes = {e["id"]: e["note"] for e in events if e["type"] == "note"}
    photos = [e for e in events if e["type"] == "photo"]
    ops = [e for e in events if e["type"] == "operator"]
    checks = [
        ("corridor completed", s["corridor_complete"]),
        ("returned home", s["returned_home"]),
        (f"recall >= {min_recall}", (s["recall"] or 0) >= min_recall),
        (f"false alarms <= {max_false_alarms}", len(s["false_alarms"]) <= max_false_alarms),
        ("every flag has a photo", all((run / f["photo"]).exists() for f in flags.values())),
    ]
    if require_notes:
        checks.append(("every flag has an LLM note", all(fid in notes and not notes[fid].get("error")
                                                         for fid in flags)))
    src = s.get("decision_sources") or {}
    clef_share = src.get("CLEF", 0) / max(1, s["decisions"])
    if min_clef_share:
        checks.append((f"Clef decided >= {min_clef_share:.0%} of decisions (measured {clef_share:.0%})",
                       clef_share >= min_clef_share))
    found = match(spec, s["flags"])
    typed = [(d, notes.get(found[d["id"]]["id"])) for d in spec["defects"] if d["id"] in found]
    note_right = sum(1 for d, n in typed if n and n.get("defect_type") == d["type"])
    ok = all(c[1] for c in checks)
    L = [f"# Patrol run report: {run.name}", "",
         f"**Result: {'PASS' if ok else 'FAIL'}**", ""]
    L += [f"- [{'x' if c[1] else ' '}] {c[0]}" for c in checks]
    L += ["", "## What ran", "",
          f"Scene `{spec['kind']}` seed {spec['seed']}, {spec['length']:.0f} m, {len(spec['defects'])} planted defects. "
          f"Versions: {json.dumps(versions())}.", "",
          f"Headline: recall {s['recall']}, false alarms {len(s['false_alarms'])}, LLM on "
          f"{(s['llm_frame_fraction'] or 0):.1%} of decisions, decision latency median {s['latency_ms']['median']} ms "
          f"(p90 {s['latency_ms']['p90']}), Clef decided {clef_share:.0%} of decisions, LLM note names the planted "
          f"defect type for {note_right}/{len(typed)} found defects, wall time {s['wall_time_s']} s.", "",
          "| measure | value |", "|---|---|"]
    for k in ("ticks", "sim_time_s", "wall_time_s", "realtime_factor", "distance_m", "battery_end", "return_reason",
              "decisions", "decisions_ok", "decision_sources", "latency_ms", "photos", "llm_calls",
              "llm_frame_fraction", "notes_ok", "recall", "false_alarms"):
        if k in s:
            L.append(f"| {k} | {json.dumps(s[k]) if isinstance(s[k], (dict, list)) else s[k]} |")
    L += ["", "## Planted defects against flags", "",
          "| defect | type | x | found by | photo triggered by | Clef's guess | LLM note |", "|---|---|---|---|---|---|---|"]
    for d in spec["defects"]:
        f = found.get(d["id"])
        n = notes.get(f["id"]) if f else None
        nt = (f"{n.get('defect_type')}, {n.get('severity')}: {n.get('note', '')[:160]}" if n and not n.get("error")
              else (n.get("error", "")[:80] if n else ""))
        L.append(f"| {d['id']} | {d['type']} | {d['x']:.0f} | {f['id'] + ' (' + f['source'] + ')' if f else 'MISSED'} | "
                 f"{f.get('trigger', '') if f else ''} | {f['guess'] if f else ''} | {nt.replace('|', '/')} |")
    if s["false_alarms"]:
        L += ["", "False alarms: " + ", ".join(
            f"{fid} at x={flags[fid]['target'][0]:.0f} (note: {notes.get(fid, {}).get('defect_type', 'none')})"
            for fid in s["false_alarms"] if fid in flags)]
    L += ["", "## Photos", "", "| photo | target x | triggered by | decided by | action | p(flag) | clearance m |",
          "|---|---|---|---|---|---|---|"]
    for p in photos:
        L.append(f"| {p['photo']} | {p['target'][0]:.0f} | {p.get('trigger', '')} | {p['gated']['source']} | "
                 f"{p['gated']['action']} | {p['decision']['probs'].get('flag_damage', 0):.2f} | "
                 f"{p.get('clearance_m')} |")
    if ops:
        L += ["", "## Operator commands", ""] + [f"- t={e['t']}: {e['command']} accepted={e['accepted']} "
                                                 f"({e['reason']})" for e in ops]
    L += ["", f"Mission log: `{run.name}/mission.jsonl`; frames and photos under `{run.name}/media/` (not in git).", ""]
    return "\n".join(L), ok, checks


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("run"); ap.add_argument("--min-recall", type=float, default=0.0)
    ap.add_argument("--max-false-alarms", type=int, default=99); ap.add_argument("--require-notes", action="store_true")
    ap.add_argument("--min-clef-share", type=float, default=0.0, help="fraction of decisions Clef must have made")
    a = ap.parse_args(argv)
    run = Path(a.run)
    text, ok, _ = build(run, a.min_recall, a.max_false_alarms, a.require_notes, a.min_clef_share)
    (run / "REPORT.md").write_text(text)
    print(f"{'PASS' if ok else 'FAIL'}: {run / 'REPORT.md'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
