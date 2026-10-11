#!/bin/sh
# patrol-ab 15:28: the corner rule (79635d3) on TUNING items only, each flight a twin of a pre-change one:
# snow2 / grass3 at a forced 21.82 m (twins runs/s4-low-tune/*-new) and grass5 on the trail with --think (twin
# runs/s4-plan-tune-grass5). Do not edit patrol/*.py while this runs.
cd "$(dirname "$0")/../.." || exit 2
I=blue_backpack,orange_tent,red_jacket,blue_tarp; C=blue_backpack,orange_tent,red_jacket
for spec in "snow 2" "grass 3"; do
  set -- $spec
  bin/patrol search --terrain $1 --seed $2 --items $I --clues $C --sweep-h 21.82 \
    --out runs/s4-corner-tune/$1$2 > logs/s4-corner-tune-$1$2.log 2>&1
  echo "$1$2 rc=$? $(date +%H:%M:%S)"
done
bin/patrol search --terrain grass --seed 5 --on-trail --think --items $I --clues $C \
  --out runs/s4-corner-tune/grass5-plan > logs/s4-corner-tune-grass5-plan.log 2>&1
echo "grass5-plan rc=$? $(date +%H:%M:%S)"
