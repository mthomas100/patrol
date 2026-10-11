#!/bin/sh
# Patrol end-to-end test with the real models (Clef-Flash on :8097, qwen38 through the gate on :8090).
# Preflight, offline tests, a seeded mission with notes, a fault-injected mission; writes runs/<ts>-e2e/REPORT.md.
# usage: tests/e2e.sh [--seed N] [--scene m2] [--skip-faults] [--out DIR]    exit 0 = PASS, 1 = FAIL, 2 = preflight
HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE" && exec "$HERE/.venv/bin/python" -m patrol.e2e "$@"
