#!/usr/bin/env bash
# Rebuild the stage fallback video from a recorded flight: replay it in the patrol console, record the page, mix the
# flight's spoken clips in where the page played them, then check the result.
#
#   tools/make_fallback.sh [RUN_DIR] [SPEED] [OUT]      defaults: runs/s6-fallback-flight  3.5  demo/fallback.mp4
#
# Needs no GPU, hold or model (the replay only streams files). The replay console runs on port 8786 and is stopped at the end.
# SPEED is sim seconds per video second: pick it so sim_s / SPEED plus the spoken summary (about 17 s) fits in 3.5 minutes
# (the s6 flight is 639 s of sim: SPEED 3 gives 3:50, 3.5 gives 3:20). The recording itself is tools/record_fallback.cjs.
# To redo only the audio mix and encode from the last recording: node tools/record_fallback.cjs --remix (same --run/--out).
# Logs: logs/s6-fallback-console.log, logs/s6-fallback-record.log. Check frames: runs/scratch/fallback-check/.
set -euo pipefail
cd "$(dirname "$0")/.."
RUN=${1:-runs/s6-fallback-flight}
SPEED=${2:-3.5}
OUT=${3:-demo/fallback.mp4}
PORT=8786
WORK=runs/scratch/fallback-build
CHECK=runs/scratch/fallback-check
mkdir -p logs "$WORK" "$CHECK"

stop_console() { pkill -f "port [8]786" 2>/dev/null || true; }     # [8] keeps pkill from matching this shell's own command line
if lsof -nP -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1; then echo "port $PORT is already in use" >&2; exit 2; fi
trap stop_console EXIT

bin/patrol console --replay "$RUN" --speed "$SPEED" --port "$PORT" > logs/s6-fallback-console.log 2>&1 &
disown $! 2>/dev/null || true          # no "Terminated" job notice when it is stopped
for _ in $(seq 1 60); do curl -sf "http://127.0.0.1:$PORT/api/state" >/dev/null && break; sleep 0.5; done
curl -sf "http://127.0.0.1:$PORT/api/state" >/dev/null || { echo "console did not start; see logs/s6-fallback-console.log" >&2; exit 3; }

node tools/record_fallback.cjs --url "http://127.0.0.1:$PORT/" --run "$RUN" --out "$OUT" --work "$WORK" 2>&1 | tee logs/s6-fallback-record.log
stop_console

echo "--- ffprobe $OUT"
ffprobe -v error -show_entries format=duration,size:stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels -of default=nw=1 "$OUT"
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT")
i=0
for f in 0.04 0.30 0.62 0.97; do
  i=$((i + 1))
  ffmpeg -v error -y -ss "$(awk -v d="$D" -v f="$f" 'BEGIN { printf "%.2f", d * f }')" -i "$OUT" -frames:v 1 "$CHECK/frame_$i.png"
done
echo "--- frames: $CHECK/frame_[1-4].png"
echo "--- audio level"
ffmpeg -hide_banner -i "$OUT" -af volumedetect -vn -f null - 2>&1 | grep -E "mean_volume|max_volume"
