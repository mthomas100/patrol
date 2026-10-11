#!/bin/sh
# patrol-ab 15:00: after the low-height A/B, run (1) a live TUNING flight with trail plans at 40 m (grass seed 5,
# on the trail, --think) to check the nearest-first remainder and the plan guard, (2) the S4 e2e with the corridor
# (scenario 5 on fresh seed 45), (3) the S6 variance runs at seed offsets 100 and 200. One Clef user at a time.
cd "$(dirname "$0")/../.." || exit 2
echo "t2 start $(date +%H:%M:%S)"
bin/patrol search --terrain grass --seed 5 --on-trail --think --items blue_backpack,orange_tent,red_jacket,blue_tarp \
  --clues blue_backpack,orange_tent,red_jacket --out runs/s4-plan-tune-grass5 > logs/s4-plan-tune-grass5.log 2>&1
echo "t2 rc=$? $(date +%H:%M:%S)"
# RUNBOOK variant (patrol-e2): the dog planted but neither in --clues nor described; pass = 2/2, no alert on the dog
bin/patrol search --terrain grass --seed 26 --think --items blue_backpack,orange_tent,grey_dog,blue_tarp \
  --clues blue_backpack,orange_tent --describe "Missing hiker. Blue backpack, orange tent." \
  --out runs/s6-runbook-variant > logs/s6-runbook-variant.log 2>&1
echo "variant rc=$? $(date +%H:%M:%S)"
tests/e2e_search.sh --with-corridor --out runs/s4-e2e-3 > logs/s4-e2e-3.log 2>&1
echo "e2e rc=$? $(date +%H:%M:%S)"
tests/e2e_search.sh --seed-offset 100 --out runs/s6-var-100 > logs/s6-var-100.log 2>&1
echo "var100 rc=$? $(date +%H:%M:%S)"
tests/e2e_search.sh --seed-offset 200 --out runs/s6-var-200 > logs/s6-var-200.log 2>&1
echo "var200 rc=$? $(date +%H:%M:%S)"
