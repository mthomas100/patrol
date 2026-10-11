"""Live console: a local web page that shows the mission as it flies (onboard camera, chase view, the decision trace,
the map, photos, notes, voice) with operator buttons and push-to-talk. The mission's events reach the page as
server-sent events; the page's commands come back as POSTs. Stdlib only.

usage: bin/patrol console [--port 8770] [--replay RUN_DIR [--speed 3]] [fly options: --scene m2 --seed 1 --escalate]
Live mode prepares a mission and waits for "start" (button or spoken). Replay mode streams a recorded mission.jsonl
(the demo's fallback when the models are unavailable, and the page's development fixture).
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import queue
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from . import mission as M

ROOT = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).parent / "console"


class Hub:
    """A mission sink that keeps every event and fans it out to the connected pages."""

    def __init__(self):
        self.history: list[dict] = []
        self.subs: list[queue.Queue] = []
        self.lock = threading.Lock()

    def __call__(self, ev: dict):
        with self.lock:
            self.history.append(ev)
            subs = list(self.subs)
        for q in subs:
            q.put(ev)

    def subscribe(self) -> tuple[queue.Queue, list[dict]]:
        q: queue.Queue = queue.Queue()
        with self.lock:
            self.subs.append(q)
            return q, list(self.history)

    def unsubscribe(self, q):
        with self.lock:
            if q in self.subs:
                self.subs.remove(q)

    def reset(self):
        with self.lock:
            self.history.clear()
        for q in list(self.subs):
            q.put({"type": "reset"})


class Console:
    def __init__(self, a):
        self.a = a
        self.hub = Hub()
        self.lock = threading.Lock()
        self.mission: M.Mission | None = None
        self.run_dir: Path | None = None
        self.running = False
        self.worker = self.speaker = None
        self.voice_n = 0
        if a.replay:
            self.run_dir = Path(a.replay).resolve()
        else:
            self.prepare()

    # ------------------------------------------------------------ live missions
    def prepare(self):
        """A fresh mission on the ground, waiting for start."""
        a = self.a
        out = ROOT / "runs" / (time.strftime("%Y%m%d-%H%M%S") + "-console")
        out.mkdir(parents=True, exist_ok=True)
        spec = M.scene(a.scene, a.seed, a.length)
        (out / "scene.json").write_text(json.dumps(spec, indent=1))
        self.jsonl = M.JsonlSink(out / "mission.jsonl")
        esc = None
        if a.escalate:
            from . import escalate
            esc = escalate.Escalator(length=a.length)
        self.mission = M.Mission(spec, out, M.Config(length=a.length, battery_start=a.battery), clef_url=a.clef_url,
                                 fault_rate=a.fault_rate, seed=a.seed, sinks=[self.jsonl, self.hub], escalator=esc,
                                 save_frames=True, realtime=not a.lockstep, chase=True)
        if a.speak or a.voice:
            from . import voice
            if self.worker is None:
                self.worker = voice.VoiceWorker()
            self.speaker = voice.Speaker(self.worker, out, publish=self.mission.emit) if a.speak else None
            if self.speaker:
                self.mission.sinks.append(self.speaker)
        self.run_dir = out
        self.hub.reset()
        self.hub({"type": "ready", "run": out.name, "scene": a.scene, "seed": a.seed, "voice": bool(self.worker),
                  "spec": {k: spec[k] for k in ("kind", "seed", "length", "spacing", "pylons", "trees")}})

    def start(self) -> bool:
        with self.lock:
            if self.running or self.a.replay:
                return False
            if self.mission is None or self.mission.ticks:
                self.prepare()
            self.running = True
        threading.Thread(target=self._fly, daemon=True).start()
        return True

    def _fly(self):
        m = self.mission
        try:
            s = m.run(self.a.max_ticks)
            if self.speaker:
                self.speaker.drain()
            s = m.summary(s["wall_time_s"])
            (m.out / "summary.json").write_text(json.dumps(s, indent=1))
            subprocess.run([str(ROOT / ".venv/bin/python"), "-m", "patrol.report", str(m.out)], cwd=ROOT,
                           capture_output=True)
            self.hub({"type": "report", "path": "REPORT.md"})
        finally:
            self.running = False

    def command(self, cmd: dict) -> dict:
        if not self.mission or not self.running:
            return {"ok": False, "error": "no mission in flight"}
        self.mission.command(cmd)
        return {"ok": True}

    def voice(self, audio: bytes, ctype: str) -> dict:
        if not self.worker or not self.mission:
            return {"ok": False, "error": "voice is off (start the console with --voice)"}
        from . import voice
        self.voice_n += 1
        d = self.run_dir / "media" / "voice"
        d.mkdir(parents=True, exist_ok=True)
        ext = "wav" if "wav" in ctype else "mp4" if "mp4" in ctype else "webm"
        raw, wav = d / f"in_{self.voice_n:02d}.{ext}", d / f"in_{self.voice_n:02d}_16k.wav"
        raw.write_bytes(audio)
        # whatever the browser recorded (webm/opus, mp4/aac, wav): 16 kHz mono 16-bit PCM for Parakeet
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-ac", "1", "-ar", "16000",
                            "-sample_fmt", "s16", str(wav)], capture_output=True, text=True)
        if r.returncode:
            return {"ok": False, "error": "ffmpeg: " + r.stderr[-200:]}
        return voice.handle_utterance(wav, self.worker, self.mission, self.speaker, self.a.clef_url,
                                      on_start=self.start)

    # ------------------------------------------------------------ replay
    def replay(self, speed: float):
        """Stream a recorded mission.jsonl, paced by its sim clock divided by speed."""
        evs = [json.loads(l) for l in (self.run_dir / "mission.jsonl").read_text().splitlines() if l.strip()]
        spec = json.loads((self.run_dir / "scene.json").read_text())
        self.hub.reset()
        self.hub({"type": "ready", "run": self.run_dir.name, "replay": True, "speed": speed,
                  "spec": {k: spec[k] for k in ("kind", "seed", "length", "spacing", "pylons", "trees") if k in spec}})
        t_prev = None
        for ev in evs:
            t = ev.get("t")
            if t is not None and t_prev is not None and t > t_prev:
                time.sleep(min(2.0, (t - t_prev) / speed))
            t_prev = t if t is not None else t_prev
            self.hub(ev)
        if (self.run_dir / "REPORT.md").exists():
            self.hub({"type": "report", "path": "REPORT.md"})

    def close(self):
        if self.worker:
            self.worker.close()


def make_handler(con: Console):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code: int, body: bytes, ctype: str = "application/json"):
            self.send_response(code)
            self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body)

        def _json(self, obj, code: int = 200):
            self._send(code, json.dumps(obj).encode())

        def _file(self, base: Path, rel: str):
            p = (base / rel).resolve()
            if not str(p).startswith(str(base.resolve())) or not p.is_file():
                return self._send(404, b"not found", "text/plain")
            self._send(200, p.read_bytes(), mimetypes.guess_type(p.name)[0] or "application/octet-stream")

        def do_GET(self):
            path = urlparse(self.path).path
            if path in ("/", "/index.html"):
                return self._file(STATIC, "index.html")
            if path.startswith("/static/"):
                return self._file(STATIC, path[len("/static/"):])
            if path.startswith("/run/") and con.run_dir:
                return self._file(con.run_dir, path[len("/run/"):])
            if path == "/api/state":
                return self._json({"running": con.running, "replay": bool(con.a.replay),
                                   "run": con.run_dir.name if con.run_dir else None, "voice": bool(con.worker)})
            if path == "/events":
                return self._events()
            self._send(404, b"not found", "text/plain")

        def _events(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream"); self.send_header("Cache-Control", "no-store")
            self.end_headers()
            q, replay = con.hub.subscribe()
            try:
                for ev in replay:
                    self.wfile.write(f"data: {json.dumps(ev)}\n\n".encode())
                self.wfile.flush()
                while True:
                    try:
                        ev = q.get(timeout=15)
                        self.wfile.write(f"data: {json.dumps(ev)}\n\n".encode())
                    except queue.Empty:
                        self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                con.hub.unsubscribe(q)

        def do_POST(self):
            path = urlparse(self.path).path
            n = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(n) if n else b""
            if path == "/api/start":
                return self._json({"ok": con.start()})
            if path == "/api/command":
                return self._json(con.command(json.loads(body or b"{}")))
            if path == "/api/voice":
                return self._json(con.voice(body, self.headers.get("Content-Type") or ""))
            self._send(404, b"not found", "text/plain")

    return H


def main(argv=None):
    p = argparse.ArgumentParser(prog="patrol console")
    M.add_args(p)
    p.add_argument("--port", type=int, default=8770)
    p.add_argument("--replay", help="stream a recorded run directory instead of flying")
    p.add_argument("--speed", type=float, default=3.0, help="replay speed (sim seconds per wall second)")
    p.add_argument("--voice", action="store_true", help="push-to-talk: Parakeet + Clef routing (implied by --speak)")
    p.add_argument("--autostart", action="store_true", help="start the mission as soon as the console is up")
    a = p.parse_args(argv)
    con = Console(a)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(con))
    srv.daemon_threads = True
    print(f"Patrol console: http://127.0.0.1:{a.port}/  run dir {con.run_dir}", flush=True)
    if a.replay:
        threading.Thread(target=con.replay, args=(a.speed,), daemon=True).start()
    elif a.autostart:
        con.start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        con.close()


if __name__ == "__main__":
    main()
