#!/bin/zsh
# S1 item library: build each search item with m3d (concept zimage-turbo, mesh hy3d, game post), then convert it
# for MuJoCo at its real size. m3d takes its own GPU hold per item (GPU.md: never wrap it in another). Items already
# converted are skipped, so the script can be re-run after a failure. Output paths must be absolute (a relative -o
# fails in the mesh stage, LOG 2026-10-11 11:50).
#
# usage: tools/build_items.sh [name ...]      (no names: the whole list below, in order)
set -u
ROOT=${0:A:h:h}
PY=$ROOT/.venv/bin/python
mkdir -p $ROOT/logs
# name | size m (largest dimension) | prompt
ITEMS=(
  "orange_tent|2.2|a small orange two-person dome camping tent, pitched, with grey poles and a closed door"
  "grey_dog|1.0|a grey husky dog lying down on its side, resting, seen whole"
  "red_jacket|0.8|a red hooded rain jacket lying flat on the ground with its arms spread out"
  "yellow_helmet|0.3|a bright yellow climbing helmet lying on its side"
  "green_sleeping_bag|2.0|a green mummy sleeping bag unrolled and lying flat"
  "orange_leaf_pile|1.4|a small low pile of orange autumn leaves"
)
want=("$@")
for row in $ITEMS; do
  name=${row%%|*}; rest=${row#*|}; size=${rest%%|*}; prompt=${rest#*|}
  if (( ${#want} )) && (( ! ${want[(Ie)$name]} )); then continue; fi
  dir=$ROOT/assets/items/$name
  if [[ -f $dir/mujoco/mujoco.json ]]; then echo "$(date +%T) $name: already converted, skipped"; continue; fi
  echo "$(date +%T) $name: m3d make (size $size m): $prompt"
  t0=$SECONDS
  m3d make "$prompt" --post game --yield-llm --seed 7 -o $dir --json > $ROOT/logs/m3d-$name.json 2> $ROOT/logs/m3d-$name.log
  rc=$?
  echo "$(date +%T) $name: m3d exit $rc after $(( SECONDS - t0 )) s"
  (( rc == 0 )) || continue
  $PY -m patrol.items convert $dir --size $size > $ROOT/logs/convert-$name.json 2>&1 \
    && echo "$(date +%T) $name: converted $(cat $ROOT/logs/convert-$name.json | tail -c 200)" \
    || echo "$(date +%T) $name: convert FAILED (logs/convert-$name.json)"
done
echo "$(date +%T) build_items done"
