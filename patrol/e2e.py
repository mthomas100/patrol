"""End-to-end test with the real models: preflight, offline tests, a seeded mission with notes, a fault-injected
mission, and runs/<ts>-e2e/REPORT.md. Exit code 0 only when every check passes (2 when the preflight fails).

usage: tests/e2e.sh [--seed N] [--scene m2] [--skip-faults] [--out DIR]
Thresholds and why they are where they are: THRESHOLDS below and DECISIONS.md (M3).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import clef, report

ROOT = Path(__file__).resolve().parents[1]
PY = str(ROOT / ".venv" / "bin" / "python")

THRESHOLDS = {
    "min_recall": 0.5,          # interim until the M3 seed sweep; see DECISIONS.md
    "max_false_alarms": 1,
    "min_clef_share": 0.80,     # the run must actually be decided by the model, not by the fallback protocol
    "max_llm_fraction": 0.10,   # the cost story: only flagged photos reach the LLM
}
KEEPER_HINT = ("Clef-Flash is kept alive by the orchestrator's keeper (GPU.md); agents never start it. Ask the "
               "orchestrator, or run: nohup ../tools/clef-keeper.sh >> "
               "~/.ds4/clef-keeper.log 2>&1 &")


def sh(cmd: list[str], log: Path | None = None, timeout: float | None = None) -> tuple[int, float, str]:
    t0 = time.time()
    if log:
        with open(log, "w") as f:
            rc = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=ROOT, timeout=timeout).returncode
        out = ""
    else:
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=timeout)
        rc, out = p.returncode, (p.stdout + p.stderr).strip()
    return rc, round(time.time() - t0, 1), out


def preflight(wait_s: float = 120.0) -> dict:
    """Clef health (waits up to wait_s, as GPU.md asks), the hold gate, memory pressure, and one tiny qwen38 call."""
    pre = {}
    t0 = time.time()
    while not clef.health(timeout=20):
        if time.time() - t0 > wait_s:
            break
        time.sleep(10)
    pre["clef_ok"] = clef.health(timeout=20)
    pre["clef_wait_s"] = round(time.time() - t0, 1)
    pre["hold_status"] = sh(["hold", "status"])[2][:300]
    mp = sh(["memory_pressure"])[2].splitlines()
    pre["memory_free"] = mp[-1].strip() if mp else "unknown"
    req = {"model": "qwen38", "max_tokens": 8, "thinking": {"type": "disabled"},
           "messages": [{"role": "user", "content": "Reply with the single word OK."}]}
    t1 = time.time()
    try:
        r = urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",
                                                          json.dumps(req).encode(),
                                                          {"Content-Type": "application/json"}), timeout=120)
        pre["qwen38"] = "ok: " + (json.loads(r.read())["choices"][0]["message"].get("content") or "")[:20].strip()
    except urllib.error.HTTPError as e:   # 503 while another agent holds the GPU: notes will wait, not fail
        pre["qwen38"] = f"HTTP {e.code} (the escalator waits out holds)"
    except Exception as e:
        pre["qwen38"] = f"unreachable: {type(e).__name__}: {e}"[:160]
    pre["qwen38_s"] = round(time.time() - t1, 1)
    return pre


def fault_checks(run: Path) -> list[tuple[str, bool]]:
    """The honest-fallback mission: dropped decisions show as FALLBACK, the protocol flies on, nothing is flagged
    on a fallback answer, and the drone still finishes and comes home."""
    s = json.loads((run / "summary.json").read_text())
    ev = [json.loads(l) for l in (run / "mission.jsonl").read_text().splitlines()]
    fb = [e for e in ev if e["type"] == "tick" and (e.get("gated") or {}).get("source") == "FALLBACK"]
    injected = [e for e in fb if "injected fault" in e["gated"]["reason"]]
    flags_on_fallback = [e for e in ev if e["type"] == "flag" and e.get("source") == "FALLBACK"]
    return [
        ("corridor completed under 30% dropped decisions", s["corridor_complete"]),
        ("returned home", s["returned_home"]),
        (f"dropped decisions shown as FALLBACK ({len(injected)} ticks)", len(injected) > 0),
        ("no flag decided by a FALLBACK answer", not flags_on_fallback),
    ]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="e2e")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--scene", default="m2")
    ap.add_argument("--fault-rate", type=float, default=0.3)
    ap.add_argument("--skip-faults", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--wait", type=float, default=120.0, help="seconds to wait for Clef /health (GPU.md: 2 min)")
    a = ap.parse_args(argv)
    out = Path(a.out) if a.out else ROOT / "runs" / (time.strftime("%Y%m%d-%H%M%S") + "-e2e")
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rows, checks = [], []

    pre = preflight(a.wait)
    (out / "preflight.json").write_text(json.dumps(pre, indent=1))
    print("preflight:", json.dumps(pre), flush=True)
    if not pre["clef_ok"]:
        checks.append(("preflight: Clef-Flash answers /health", False))
        write(out, a, pre, rows, checks, t0, extra=[KEEPER_HINT])
        print(KEEPER_HINT)
        sys.exit(2)

    rc, wall, _ = sh([PY, "-m", "pytest", "-q", "tests/"], out / "pytest.log")
    rows.append(("offline tests (pytest)", wall, "pytest.log")); checks.append(("offline tests pass", rc == 0))

    mrun = out / "mission"
    rc, wall, _ = sh([str(ROOT / "bin" / "patrol"), "fly", "--scene", a.scene, "--seed", str(a.seed), "--escalate",
                      "--out", str(mrun)], out / "mission.log")
    rows.append((f"mission: {a.scene} seed {a.seed}, Clef + qwen38 notes", wall, "mission/REPORT.md"))
    if rc != 0 or not (mrun / "summary.json").exists():
        checks.append(("mission ran", False))
    else:
        text, ok, mchecks = report.build(mrun, THRESHOLDS["min_recall"], THRESHOLDS["max_false_alarms"], True,
                                         THRESHOLDS["min_clef_share"])
        (mrun / "REPORT.md").write_text(text)
        s = json.loads((mrun / "summary.json").read_text())
        checks += [(f"mission: {c[0]}", bool(c[1])) for c in mchecks]
        checks += [
            (f"LLM fraction reported and <= {THRESHOLDS['max_llm_fraction']:.0%} (measured "
             f"{(s['llm_frame_fraction'] or 0):.1%})",
             s["llm_frame_fraction"] is not None and s["llm_frame_fraction"] <= THRESHOLDS["max_llm_fraction"]),
            (f"decision latency reported (median {s['latency_ms']['median']} ms, p90 {s['latency_ms']['p90']} ms)",
             s["latency_ms"]["median"] is not None),
        ]

    if not a.skip_faults:
        frun = out / "faults"
        rc, wall, _ = sh([str(ROOT / "bin" / "patrol"), "fly", "--scene", a.scene, "--seed", str(a.seed),
                          "--fault-rate", str(a.fault_rate), "--out", str(frun)], out / "faults.log")
        rows.append((f"fault mission: {a.fault_rate:.0%} of decisions dropped", wall, "faults/REPORT.md"))
        if rc != 0 or not (frun / "summary.json").exists():
            checks.append(("fault mission ran", False))
        else:
            text, _, _ = report.build(frun, 0.0, 99, False)
            (frun / "REPORT.md").write_text(text)
            checks += fault_checks(frun)

    ok = write(out, a, pre, rows, checks, t0)
    print(f"{'PASS' if ok else 'FAIL'}: {out / 'REPORT.md'}")
    sys.exit(0 if ok else 1)


def write(out: Path, a, pre: dict, rows: list, checks: list, t0: float, extra: list | None = None) -> bool:
    ok = bool(checks) and all(c[1] for c in checks)
    L = [f"# Patrol e2e report: {out.name}", "", f"**Result: {'PASS' if ok else 'FAIL'}**", "",
         f"Command: `tests/e2e.sh --scene {a.scene} --seed {a.seed}`; total wall time {time.time() - t0:.0f} s. "
         f"Versions: {json.dumps(report.versions())}.", "",
         f"Thresholds: {json.dumps(THRESHOLDS)} (justified in DECISIONS.md, M3).", "", "## Checks", ""]
    L += [f"- [{'x' if c[1] else ' '}] {c[0]}" for c in checks]
    L += ["", "## Steps", "", "| step | wall s | detail |", "|---|---|---|"]
    L += [f"| {r[0]} | {r[1]} | `{r[2]}` |" for r in rows]
    L += ["", "## Preflight", "", "```", json.dumps(pre, indent=1), "```", ""]
    if extra:
        L += extra + [""]
    (out / "REPORT.md").write_text("\n".join(L))
    return ok


if __name__ == "__main__":
    main()
