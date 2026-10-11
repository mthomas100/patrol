"""Build the description read-back for a flight that was recorded from the CLI (the CLI flight has none).

The live console reads the clues back after a spoken description: "Looking for <words>; <words>." (console.on_describe ->
voice.clue_options_text, said by the Kokoro voice as speech event "clues_0"). `bin/patrol search --describe-wav ...` only
prints them, so a recorded CLI flight has no such clip. This writes the same line, with the same voice, as
<run>/media/audio/clues_0.wav and <run>/media/audio/clues_0.txt (the exact words), for tools/record_fallback.cjs to play
at takeoff in the fallback video. It is a constructed addition, made after the flight; nothing else in the run changes.
Parakeet and Kokoro need no GPU hold (GPU.md); the worker exits when this script ends.

usage: .venv/bin/python -m tools.make_readback runs/s6-fallback-flight
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from patrol import voice


def main(run_dir: str) -> int:
    run = Path(run_dir)
    d = json.loads((run / "describe.json").read_text())
    text = voice.clue_options_text(d)
    out = run / "media" / "audio" / "clues_0.wav"
    out.parent.mkdir(parents=True, exist_ok=True)
    worker = voice.VoiceWorker()
    try:
        r = worker.tts(text, out)
    finally:
        worker.close()
    if not r.get("ok"):
        print("TTS failed:", r.get("error"), file=sys.stderr)
        return 1
    out.with_suffix(".txt").write_text(text + "\n")
    print(json.dumps({"wav": str(out), "text": text, "audio_s": r.get("audio_s"), "tts_ms": r.get("tts_ms")}))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    raise SystemExit(main(sys.argv[1]))
