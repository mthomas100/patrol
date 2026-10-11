#!/bin/sh
# Patrol search e2e (S4): five scenarios with the real models on held-out items -> runs/<ts>-e2e-search/REPORT.md
# usage: tests/e2e_search.sh [--only 1,3] [--with-corridor] [--out DIR]    exit 0 = PASS, 1 = FAIL, 2 = preflight
HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE" && exec "$HERE/.venv/bin/python" -m patrol.e2e_search "$@"
