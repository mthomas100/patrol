"""Patrol's ears and voice: one long-lived process holding Parakeet (speech in) and Kokoro (speech out), reusing
~/repos/local-voice's engines and its adapter settings. Run it with local-voice's venv python (patrol.voice does).

Protocol: one JSON request per stdin line, one JSON reply per stdout line, prefixed "PATROL_VOICE ".
  {"op": "stt", "wav": "in.wav"}                -> {"ok", "text", "stt_ms", "audio_s"}
  {"op": "tts", "text": "...", "out": "o.wav"}  -> {"ok", "wav", "tts_ms", "audio_s"}
The first line it prints is {"ready": true, ...load times...}. It exits on EOF, so the mission's end stops it
(GPU.md: speech models need no hold, but exit when the stage ends; one process per project).
"""
from __future__ import annotations

import json
import sys
import time
import wave
from pathlib import Path

LV = Path.home() / "repos/local-voice/orchestrator"
sys.path.insert(0, str(LV))

import numpy as np  # noqa: E402
import yaml  # noqa: E402


def settings(section: str, name: str) -> dict:
    return dict(yaml.safe_load((LV / "config.yaml").read_text())[section]["adapters"][name])


def read_wav(path: str, rate: int) -> np.ndarray:
    with wave.open(path, "rb") as w:
        n, ch, sw, sr = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
        raw = w.readframes(n)
    if sw != 2:
        raise ValueError(f"{path}: need 16-bit PCM WAV, got {8 * sw}-bit")
    a = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if ch > 1:
        a = a.reshape(-1, ch).mean(axis=1)
    if sr != rate:
        t = np.arange(int(len(a) * rate / sr)) * (sr / rate)
        a = np.interp(t, np.arange(len(a)), a).astype(np.float32)
    return a


def write_wav(path: str, audio: np.ndarray, rate: int) -> None:
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())


def reply(obj: dict) -> None:
    sys.stdout.write("PATROL_VOICE " + json.dumps(obj) + "\n"); sys.stdout.flush()


def main() -> None:
    from local_voice.engines.kokoro import KokoroEngine
    from local_voice.engines.parakeet import ParakeetEngine
    s_stt, s_tts = settings("stt", "parakeet"), settings("tts", "kokoro")
    stt, tts = ParakeetEngine(s_stt), KokoroEngine(s_tts)
    stt.load(); stt.warm(); tts.load(); tts.warm()
    reply({"ready": True, "stt_model": s_stt["model"], "tts_model": s_tts["model"], "voice": s_tts.get("voice"),
           "stt_load_s": stt.load_s, "tts_load_s": tts.load_s})
    for line in sys.stdin:
        try:
            req = json.loads(line)
            t0 = time.monotonic()
            if req["op"] == "stt":
                audio = read_wav(req["wav"], stt.sample_rate)
                text = stt.transcribe(audio)
                reply({"ok": True, "text": text, "stt_ms": round((time.monotonic() - t0) * 1000, 1),
                       "audio_s": round(len(audio) / stt.sample_rate, 2)})
            elif req["op"] == "tts":
                chunks = list(tts.stream(req["text"]))
                audio = np.concatenate(chunks) if chunks else np.zeros(1, np.float32)
                write_wav(req["out"], audio, tts.sample_rate)
                reply({"ok": True, "wav": req["out"], "tts_ms": round((time.monotonic() - t0) * 1000, 1),
                       "audio_s": round(len(audio) / tts.sample_rate, 2)})
            else:
                reply({"ok": False, "error": f"unknown op {req.get('op')}"})
        except Exception as e:      # one bad request must not kill the operator's voice for the rest of the run
            reply({"ok": False, "error": f"{type(e).__name__}: {e}"[:300]})


if __name__ == "__main__":
    main()
