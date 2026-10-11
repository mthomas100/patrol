#!/bin/sh
# S4 low-height A/B on TUNING items only (DECISIONS 14:55): forced 21.82 m sweep (scenario 5's height), no --think.
# arm "new": planner.frame_spacing (6.54 m at 21.82 m); arm "old12": the fixed 12 m it replaced.
cd "$(dirname "$0")/../.." || exit 2
I=blue_backpack,orange_tent,red_jacket,blue_tarp; C=blue_backpack,orange_tent,red_jacket
for spec in "snow 2" "grass 3"; do
  set -- $spec
  for arm in new old12; do
    extra=""; [ "$arm" = old12 ] && extra="--frame-every 12"
    bin/patrol search --terrain $1 --seed $2 --items $I --clues $C --sweep-h 21.82 $extra \
      --out runs/s4-low-tune/$1$2-$arm > logs/s4-low-tune-$1$2-$arm.log 2>&1
    echo "$1$2-$arm rc=$?"
  done
done
