#!/bin/sh
# patrol-ab 15:56: the 30-minute battery (8a3867b) on the e2e (base seeds, with the corridor) and fresh offsets 300, 400.
# Do not edit patrol/*.py while this runs (each scenario starts a fresh process).
cd "$(dirname "$0")/.." || exit 2
tests/e2e_search.sh --with-corridor --out runs/s4-e2e-4 > logs/s4-e2e-4.log 2>&1; echo "e2e-4 rc=$? $(date +%H:%M:%S)"
tests/e2e_search.sh --seed-offset 300 --out runs/s6-var-300 > logs/s6-var-300.log 2>&1; echo "var300 rc=$? $(date +%H:%M:%S)"
tests/e2e_search.sh --seed-offset 400 --out runs/s6-var-400 > logs/s6-var-400.log 2>&1; echo "var400 rc=$? $(date +%H:%M:%S)"
