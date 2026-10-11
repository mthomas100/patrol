"""Search e2e (S4): the five scenarios of the testing doctrine, with the real models, on held-out items.

  1 item present   a held-out clue and its decoy: found, right clue, alert within MATCH_R of the true spot
  2 decoys         decoys only, while the family's clues are searched for: no alert
  3 empty          nothing planted: a full sweep with no alert
  4 Clef off       the decision link is dead: the sweep finishes on FALLBACK and the drone comes home, no alert
  5 several        four held-out clues and two decoys: each clue alerted once (no duplicates)
  6 voice          the operator speaks the description (qwen38 writes the clues Clef uses), alerts are read aloud,
                   "go back to the last alert" and "stop searching and come home" are heard, routed and executed

Each scenario is one `bin/patrol search --think` flight (realtime: the drone keeps flying while Clef thinks; qwen38 on
board for notes, trail plans and second opinions). Ground truth is read only by search.score() after each flight. Writes runs/<ts>-e2e-search/REPORT.md; exit 0 = PASS, 1 = FAIL,
2 = preflight failed. usage: tests/e2e_search.sh [--only 1,3] [--with-corridor] [--no-think] [--out DIR]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

from . import report
from .e2e import PY, ROOT, preflight, sh

MATCH_R = 5.0           # metres between an alert and the planted item for a find
DEAD = "http://127.0.0.1:9/v1/systemone"
SCENARIOS = {   # held out: grey_dog, green_sleeping_bag, yellow_helmet, sos_rocks; decoys built for them
    1: {"name": "item present", "terrain": "grass", "seed": 21, "items": "grey_dog,grey_boulder", "clues": "grey_dog"},
    2: {"name": "decoys", "terrain": "snow", "seed": 22, "items": "blue_tarp,red_rock,orange_leaf_pile,grey_boulder",
        "clues": "blue_backpack,red_jacket,orange_tent,grey_dog"},
    3: {"name": "empty", "terrain": "grass", "seed": 23, "items": "", "clues": "blue_backpack,orange_tent,grey_dog"},
    4: {"name": "Clef off", "terrain": "snow", "seed": 24, "items": "blue_backpack", "clues": "blue_backpack",
        "extra": ["--clef-url", DEAD, "--half", "50"]},
    5: {"name": "several", "terrain": "snow", "seed": 35,      # seed 25 was diagnosed after s4-e2e-1 (DECISIONS 13:50)
        "items": "grey_dog,green_sleeping_bag,yellow_helmet,sos_rocks,grey_boulder,orange_leaf_pile",
        "clues": "grey_dog,green_sleeping_bag,yellow_helmet,sos_rocks"},
    6: {"name": "voice", "terrain": "grass", "seed": 26, "items": "blue_backpack,orange_tent,grey_dog,blue_tarp",
        "clues": "blue_backpack,orange_tent,grey_dog",
        "extra": ["--describe-wav", "fixtures/voice/describe_demo.wav", "--speak", "--voice-script",
                  json.dumps({"alert:1": "fixtures/voice/go_back_alert.wav",
                              "alert:2": "fixtures/voice/return_home_search.wav"})]},
}


def voice_checks(d: Path, s: dict, sc: dict) -> list[tuple[str, bool]]:
    from .search import _same_item
    desc = json.loads((d / "describe.json").read_text()) if (d / "describe.json").exists() else {}
    cl = desc.get("clues", [])
    want = SCENARIOS[6]["clues"].split(",")
    named = [w for w in want if any(_same_item({"clue": c["name"], "family": c["family"]}, w) for c in cl)]
    evs = [json.loads(l) for l in (d / "mission.jsonl").read_text().splitlines()]
    speech = [e for e in evs if e["type"] == "speech" and e.get("audio")]
    said = {e.get("alert") for e in speech if e.get("alert")}
    ops = [e for e in evs if e["type"] == "operator"]
    voice = [e for e in evs if e["type"] == "voice"]
    did = lambda name: any(e["accepted"] and e["command"].get("name") == name for e in ops)
    return [(f"S6: heard \"{desc.get('text', '?')}\"; qwen38's clue options name {named} of {want} "
             f"({[c['name'] for c in cl]})", len(named) == len(want)),
            (f"S6: every alert read aloud ({sorted(said)} of {[a['id'] for a in s['alerts']]})",
             bool(s["alerts"]) and all(a["id"] in said for a in s["alerts"])),
            (f"S6: 'go back to the last alert' heard, routed and executed "
             f"({[(e.get('text'), e.get('route'), e.get('source')) for e in voice][:2]})", did("go_back_to_last_alert")),
            (f"S6: 'stop searching and come home' executed, flight ended at home ({s['return_reason']})",
             did("return_home") and s["state"] == "DONE"),
            (f"S6: no false alert ({sc['false_alerts']})", not sc["false_alerts"])]


def checks_for(k: int, s: dict, sc: dict, d: Path | None = None) -> list[tuple[str, bool]]:
    alerts = s["alerts"]
    if k == 6:
        return voice_checks(d, s, sc)
    home = s["state"] == "DONE"
    out = [(f"S{k}: flight ended at home ({s['return_reason']})", home)]
    if k == 1:
        r = next(r for r in sc["items"] if r["role"] == "clue")
        out += [(f"S1: {r['name']} noticed by the finder ({r['noticed']} of {r['frames_in_view']} frames in view)",
                 r["noticed"] > 0),
                (f"S1: investigated ({r['investigated']}) and alerted with the right clue", r["right_clue"]),
                (f"S1: alert within {MATCH_R:.0f} m (error {r['loc_err_m']} m)", r["loc_err_m"] is not None
                 and r["loc_err_m"] <= MATCH_R),
                (f"S1: no false alert ({sc['false_alerts']})", not sc["false_alerts"])]
    elif k in (2, 3):
        out += [(f"S{k}: no alert (got {[a['id'] + ' ' + a['clue'] for a in alerts]}; decoys investigated "
                 f"{sc['decoys_investigated']})", not alerts),
                (f"S{k}: area covered ({100 * s['coverage']:.0f}%)", s["coverage"] >= 0.95)]
    elif k == 4:
        n = s["clef_sweep"]["n"] + s["clef_confirm"]["n"]
        out += [(f"S4: every answer was FALLBACK ({s['fallback']} of {n})", n > 0 and s["fallback"] == n),
                (f"S4: the sweep finished ({100 * s['coverage']:.0f}% covered, {s['return_reason']})",
                 s["return_reason"] == "area covered"),
                ("S4: no alert", not alerts)]
    elif k == 5:
        clue_rows = [r for r in sc["items"] if r["role"] == "clue"]
        dup = [r["name"] for r in clue_rows if len(r["alerts"]) > 1]
        out += [(f"S5: every clue found ({sc['recall']}; missed "
                 f"{[r['name'] for r in clue_rows if not r['right_clue']]})", sc["found"] == sc["clues"]),
                (f"S5: no duplicate alerts ({dup})", not dup),
                (f"S5: no false alert ({sc['false_alerts']})", not sc["false_alerts"])]
    return out


def metrics(k: int, s: dict, sc: dict) -> str:
    cands = s.get("candidates") or 0
    sw, cf = s["clef_sweep"], s["clef_confirm"]
    calls = sw["n"] + cf["n"]
    qi, qa = s.get("clef_qwen_idle") or {}, s.get("clef_qwen_active") or {}
    per_batt = round(s["area_m2_covered"] / max(s["battery_used_pct"], 1e-6) * 100) if s["area_m2_covered"] else None
    return (f"| {k} {SCENARIOS[k]['name']} | {sc['recall']} | {len(sc['false_alerts'])} | {sc['time_to_first_find']} | "
            f"{sc['loc_err_m']} | {100 * s['coverage']:.0f}% | {per_batt} | {s['frames']} | {calls} "
            f"({calls / max(s['frames'], 1):.2f}/frame) | {s.get('llm_calls', 0)} | {len(s['alerts'])}/{cands} | "
            f"{s['investigations']} ({s['mean_investigate_s']} s, {s['mean_decision_h']} m) | {sw['median_ms']}/{sw['p90_ms']} | "
            f"{cf['median_ms']}/{cf['p90_ms']} | {qi.get('median_ms')}/{qi.get('p90_ms')} (n {qi.get('n')}) | "
            f"{qa.get('median_ms')}/{qa.get('p90_ms')} (n {qa.get('n')}) | {s.get('llm_by_role') or {}} | "
            f"{s['sim_s']} | {s['wall_s']} |")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tests/e2e_search.sh")
    ap.add_argument("--only", default="1,2,3,4,5,6")
    ap.add_argument("--no-think", action="store_true", help="fly without qwen38 on board (Clef only)")
    ap.add_argument("--with-corridor", action="store_true", help="also run the power-line regression e2e (seed 1)")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    t0 = time.time()
    out = Path(a.out or ROOT / "runs" / time.strftime("%Y%m%d-%H%M%S-e2e-search"))
    out.mkdir(parents=True, exist_ok=True)
    pre = preflight()
    rows, checks, table = [], [], []
    if not pre["clef_ok"]:
        (out / "REPORT.md").write_text(f"# Search e2e: preflight failed\n\n```\n{json.dumps(pre, indent=1)}\n```\n")
        print(f"PREFLIGHT FAILED: Clef-Flash not answering. {out}/REPORT.md"); return 2
    rc, dt, _ = sh([PY, "-m", "pytest", "-q", "tests/"], log=out / "pytest.log")
    rows.append(("offline tests", dt, (out / "pytest.log").read_text().strip().splitlines()[-1]))
    checks.append(("offline tests pass", rc == 0))
    for k in [int(x) for x in a.only.split(",") if x]:
        sc_ = SCENARIOS[k]
        d = out / f"s{k}"
        cmd = [PY, "-m", "patrol.cli", "search", "--terrain", sc_["terrain"], "--seed", str(sc_["seed"]),
               "--items", sc_["items"], "--clues", sc_["clues"], "--out", str(d)] + sc_.get("extra", []) \
            + ([] if a.no_think else ["--think"])
        rc, dt, _ = sh(cmd, log=out / f"s{k}.log", timeout=1800)
        rows.append((f"S{k} {sc_['name']}", dt, " ".join(cmd[3:])))
        if rc != 0 or not (d / "summary.json").exists():
            checks.append((f"S{k}: flight ran (exit {rc}, log s{k}.log)", False)); continue
        s, sc = json.loads((d / "summary.json").read_text()), json.loads((d / "score.json").read_text())
        checks += checks_for(k, s, sc, d)
        table.append(metrics(k, s, sc))
    if a.with_corridor:
        rc, dt, _ = sh([PY, "-m", "patrol.e2e", "--seed", "1", "--out", str(out / "corridor")],
                       log=out / "corridor.log", timeout=3600)
        rows.append(("corridor regression (seed 1)", dt, "patrol.e2e --seed 1"))
        checks.append(("power-line regression e2e passes (corridor/REPORT.md)", rc == 0))
    ok = all(c[1] for c in checks)
    L = [f"# Patrol search e2e: {out.name}", "", f"**Result: {'PASS' if ok else 'FAIL'}**", "",
         f"Command: `tests/e2e_search.sh --only {a.only}{' --with-corridor' if a.with_corridor else ''}"
         f"{' --no-think' if a.no_think else ''}`; total wall "
         f"time {time.time() - t0:.0f} s. Versions: {json.dumps(report.versions())}.", "",
         "Held-out items: grey_dog, green_sleeping_bag, yellow_helmet, sos_rocks (never used for tuning). Decoys: "
         "grey_boulder, red_rock, orange_leaf_pile, blue_tarp. Scenario 6 (voice) uses tuning items plus the grey dog "
         "and qwen38's own clue wording from the spoken description. Thresholds and rules: DECISIONS 2026-10-11 "
         "(patrol-aa, patrol-5d); the e2e pass bars are justified in DECISIONS 2026-10-11 patrol-5d (S4).",
         "", "## Checks", ""] + [f"- [{'x' if c[1] else ' '}] {c[0]}" for c in checks]
    L += ["", "## Metrics", "", "| scenario | recall | false alerts | first find s | loc err m | covered | m² per "
          "battery | frames | Clef calls | LLM calls | alerts/candidates | investigations (mean s, decision h) | "
          "sweep ms p50/p90 | confirm ms p50/p90 | Clef ms, qwen38 idle | Clef ms, qwen38 busy | qwen38 calls by role "
          "| sim s | wall s |", "|" + "---|" * 19] + table
    L += ["", "## Steps", "", "| step | wall s | detail |", "|---|---|---|"] + [f"| {r[0]} | {r[1]} | `{r[2]}` |"
                                                                              for r in rows]
    L += ["", "## Preflight", "", "```", json.dumps(pre, indent=1), "```", ""]
    (out / "REPORT.md").write_text("\n".join(L))
    print(f"{'PASS' if ok else 'FAIL'}: {out}/REPORT.md")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
