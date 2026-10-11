"""The closed loop: render -> Clef decides -> gate -> state machine -> sim step, one control tick at a time.

Every tick and every notable event goes to the sinks as a dict with a "type" (tick, photo, flag, operator, state,
summary). The JSONL mission log is one sink; the live console (M4) and TTS (M4) are further sinks. Operator commands
(spoken commands after Clef routes them, M4) enter through Mission.command() and are applied at the next tick.
"""
from __future__ import annotations

import json
import random
import statistics
import threading
import time
from collections import deque
from pathlib import Path

from . import clef, world
from .control import (ACTIONS, CRUISE_WEIGHTS, Config, Flag, Gated, StateMachine, Target, confirm_gate, gate,
                      rangefinder_flag)
from .sim import Sim

ROOT = Path(__file__).resolve().parents[1]
W, H = 512, 384


class JsonlSink:
    def __init__(self, path: Path):
        self.f = open(path, "w")
        self.lock = threading.Lock()

    def __call__(self, ev: dict):
        with self.lock:            # notes arrive from the escalation thread
            self.f.write(json.dumps(ev) + "\n"); self.f.flush()

    def close(self):
        self.f.close()


class Mission:
    def __init__(self, spec: dict, out: Path, cfg: Config | None = None, clef_url: str = clef.URL,
                 fault_rate: float = 0.0, seed: int = 0, sinks=(), escalator=None, save_frames: bool = True,
                 realtime: bool = True, chase: bool = False):
        self.spec, self.out = spec, Path(out)
        self.cfg = cfg or Config(length=spec["length"])
        self.sim = Sim(spec, start=self.cfg.home)
        self.sm = StateMachine(self.cfg)
        self.clef_url, self.fault_rate = clef_url, fault_rate
        self.rng = random.Random(seed + 101)
        self.sinks = list(sinks)
        self.escalator = escalator          # callable(flag, photo_bytes) -> note dict, run off the control path
        self.commands: deque = deque()
        self.save_frames = save_frames
        self.ticks = 0
        self.v_prev = (0.0, 0.0, 0.0)
        self.latency_ema = 0.0
        self.realtime = realtime
        self.chase = chase              # also render the third-person chase camera each tick (console, demo video)
        self.started = False
        self.decisions: list[dict] = []
        self.photos: list[dict] = []
        (self.out / "media" / "frames").mkdir(parents=True, exist_ok=True)
        (self.out / "media" / "photos").mkdir(parents=True, exist_ok=True)
        if chase:
            (self.out / "media" / "chase").mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------ plumbing
    def emit(self, type_: str, **data):
        ev = {"type": type_, "t": round(self.sim.t, 2), **data}
        for s in self.sinks:
            s(ev)
        return ev

    def command(self, cmd: dict):
        self.commands.append(cmd)

    def _ask(self, jpeg: bytes, state: str, questions: dict):
        if self.fault_rate and self.rng.random() < self.fault_rate:
            return clef.Decision(ok=False, error="injected fault: decision link dropped")
        return clef.ask(jpeg, state, questions, timeout=6.0, url=self.clef_url)

    def _ctx(self, **kw):
        here = [f.id for f in self.sm.flags if abs(f.target.x - self.sim.pos[0]) < 10]
        return {"length": self.cfg.length, "flags_here": ", ".join(here), **kw}

    # ------------------------------------------------------------ one tick
    def tick(self):
        sm, sim, cfg = self.sm, self.sim, self.cfg
        pos, speed = tuple(sim.pos), float((sim.vel ** 2).sum() ** 0.5)
        rec = {"tick": self.ticks, "state_in": sm.state}
        g: Gated | None = None
        while self.commands:
            cmd = self.commands.popleft()
            og = sm.operator(cmd)
            self.emit("operator", command=cmd, accepted=og is not None, reason=og.reason if og else "not applicable")
            if og:
                g = og
        sm.drain(cfg.dt)
        sg = sm.safety(pos, speed)
        if sg:
            g = sg
            self.emit("state", state=sm.state, reason=sg.reason)
        v = (0.0, 0.0, 0.0)
        frame_file = None
        if sm.state == "CRUISE":
            lt = world.look_target(self.spec, pos[0], phase=sm.phase)
            look = Target(*lt, why=world.describe_target(self.spec, lt, sm.phase))
            tower_ahead = any(pos[0] - 2 <= p["x"] <= pos[0] + 17 for p in self.spec["pylons"])
            sim.aim("inspect", (look.x, look.y, look.z))
            jpg = sim.jpeg("inspect", W, H)
            frame_file = self._save("frames", f"t{self.ticks:04d}.jpg", jpg)
            # the rangefinder (a few ms) runs first: a measured encroachment needs no model to stop the drone
            rf = sim.vegetation_clearance("inspect", where=True, x_window=(pos[0] - 2, pos[0] + 14)) \
                if self.spec["kind"] == "corridor" else None
            g2 = sm.on_rangefinder(rf, pos[0])
            if g2 is None:
                dec = self._ask(jpg, clef.state_text(sim.telemetry(), self._ctx()), clef.schema())
                moved = self._fly_blind(dec)
                pos = tuple(sim.pos)
                fa, fw = sm.fallback_cruise(pos[0], look, tower_ahead)
                g2 = sm.on_cruise(gate(dec, ACTIONS, CRUISE_WEIGHTS, fa, fw, moved_m=moved), look, dec)
                rec["decision"] = self._dec(dec, "cruise")
            g = g or g2
            rec.update(aim=[look.x, look.y, look.z],
                       rangefinder=min((r["clearance"] for r in rf.values()), default=None) if rf else None)
            if sm.state == "CRUISE":
                v = sm.velocity_hold(pos, sm.governed_cruise(self.latency_ema))
            else:
                v = sm.velocity_hold(pos, 0.0)
                self.emit("state", state=sm.state, reason=f"{g2.label}: {g2.action}"
                          + (f" ({g2.reason})" if g2.reason else ""))
        elif sm.state == "HOVER":
            v = sm.velocity_hold(pos, 0.0)
            if speed < 0.3:
                sm.hover_ticks += 1
            if sm.hover_ticks >= cfg.hover_hold_ticks:
                g = self._photograph() or g
        elif sm.state == "REVISIT":
            t = sm.target
            if pos[0] > t.x - 6:
                v = sm.velocity_hold(pos, -cfg.revisit_speed)
                sim.aim("inspect", (t.x, t.y, t.z))
            else:
                sm.state, sm.hover_ticks = "HOVER", 0
                self.emit("state", state="HOVER", reason=f"revisit reached x={t.x:.0f}")
        elif sm.state == "RETURN":
            v = self._return_velocity(pos)
        rec.update(state=sm.state, gated=self._g(g), frame=frame_file, battery=round(sm.battery, 1),
                   tel=sim.telemetry(), truth=sim.visible_defects("inspect", W, H) if frame_file else [])
        rec["cruise_speed"] = round(sm.governed_cruise(self.latency_ema), 2)
        if self.chase:
            rec["chase"] = self._save("chase", f"c{self.ticks:04d}.jpg", sim.jpeg("chase", 480, 360, quality=80),
                                      force=True)
        self.emit("tick", **rec)
        sim.step(v, cfg.dt)
        self.v_prev = v
        self.ticks += 1

    def _photograph(self) -> Gated:
        """Hover photo. A tower target is one zoom on the insulator string; a mid-span target is a pair of zooms
        3 m behind and ahead of the aim point (the look-ahead aim is only good to a few metres), decided together."""
        sm, sim = self.sm, self.sim
        t = sm.target
        offsets = (0.0,) if "insulator string" in t.why else (-3.0, 3.0)
        jpgs, paths, clear = [], [], []
        n = len(self.photos) + 1
        for k, off in enumerate(offsets):
            sim.aim("zoom", (t.x + off, t.y, t.z))
            jpg = sim.jpeg("zoom", W, H)
            jpgs.append(jpg)
            c = sim.vegetation_clearance("zoom", x_window=(t.x + off - 8, t.x + off + 8))
            if c is not None:
                clear.append(c)
            paths.append(self._save("photos", f"photo_{n:02d}{'ab'[k] if len(offsets) > 1 else ''}_x{t.x + off:05.1f}.jpg",
                                    jpg, force=True))
        path = paths[0]
        clearance = min(clear) if clear else None
        dec = self._ask(jpgs if len(jpgs) > 1 else jpgs[0],
                        clef.state_text(sim.telemetry(), self._ctx(camera="zoom2" if len(jpgs) > 1 else "zoom",
                                                                   hovering=True, clearance=clearance)),
                        clef.confirm_schema())
        self._fly_blind(dec)
        g = rangefinder_flag(confirm_gate(dec, "protocol: no flag without a confident confirmation; photo kept for "
                                               "human review"), clearance)
        truth = []
        for off in offsets:
            sim.aim("zoom", (t.x + off, t.y, t.z))
            truth += [v for v in sim.visible_defects("zoom", W, H, max_depth=40) if v["id"] not in {x["id"] for x in truth}]
        photo = {"photo": path, "photos": paths, "target": [t.x, t.y, t.z], "what": t.why, "clearance_m": clearance,
                 "trigger": sm.trigger,
                 "decision": self._dec(dec, "confirm"), "gated": self._g(g), "truth": truth}
        self.photos.append(photo)
        self.emit("photo", **photo)
        if g.action == "flag_damage":
            guess = "vegetation_close" if g.source == "sensor" else \
                max(dec.nouls, key=dec.nouls.get) if dec.nouls else "unknown"
            prev = next((x for x in sm.flags if x.target.near(t)), None)
            if prev:        # a re-inspection (spoken revisit): the same finding gets a fresh photo and note
                f = prev
                f.photo, f.probs, f.nouls, f.t, f.note = path, dec.probs, dec.nouls, sim.t, None
            else:
                f = Flag(id=f"F{len(sm.flags) + 1}", target=t, photo=path, t=sim.t, probs=dec.probs,
                         nouls=dec.nouls, defect_guess=guess, source=g.label, clearance=clearance,
                         trigger=sm.trigger)
                sm.flags.append(f)
            self.emit("flag", id=f.id, target=[t.x, t.y, t.z], photo=path, photos=paths, defect_guess=guess,
                      clearance_m=clearance, trigger=sm.trigger, source=g.label, revisit=bool(prev),
                      probs=dec.probs, nouls=dec.nouls, truth=photo["truth"])
            if self.escalator:     # off the control path; the note event arrives when qwen38 answers
                self.escalator.submit(f, jpgs if len(jpgs) > 1 else jpgs[0], lambda fl, note: self.emit("note", id=fl.id, photo=fl.photo,
                                                                          note=note))
        sm.on_confirm(g)
        return g

    def _fly_blind(self, dec) -> float:
        """Real-time honesty: while the model thinks, the drone keeps flying its last command (lockstep pauses
        the world instead when realtime is off). Feeds the speed governor; returns metres flown while waiting."""
        lat = dec.latency_ms / 1000.0
        if dec.ok or lat > 0:
            self.latency_ema = lat if self.latency_ema == 0 else 0.7 * self.latency_ema + 0.3 * lat
        if self.realtime and lat > 0:
            before = self.sim.pos.copy()
            self.sim.step(self.v_prev, min(lat, 10.0))
            return float(((self.sim.pos - before) ** 2).sum() ** 0.5)
        return 0.0

    def _return_velocity(self, pos):
        cfg, sm = self.cfg, self.sm
        hx, hy, hz = cfg.home
        dx, dy = hx - pos[0], hy - pos[1]
        dist_xy = (dx * dx + dy * dy) ** 0.5
        if dist_xy < 1.0:
            if abs(pos[2] - hz) < 0.3 and float((self.sim.vel ** 2).sum()) < 0.05:
                sm.state = "DONE"
                self.emit("state", state="DONE", reason=f"home ({sm.return_reason})")
            return (dx, dy, 0.8 * (hz - pos[2]))
        s = min(cfg.transit, dist_xy) / dist_xy
        return (dx * s, dy * s, 0.8 * (cfg.transit_altitude - pos[2]))

    def status_text(self) -> str:
        """One paragraph of mission state for voice routing and spoken questions."""
        sm, tel = self.sm, self.sim.telemetry()
        if not self.started:
            return (f"The drone is on the ground at the launch point, ready to patrol the {self.cfg.length:.0f} m "
                    f"corridor; battery {sm.battery:.0f}%.")
        flags = "; ".join(f"{f.id} at {f.target.x:.0f} m ({(f.note or {}).get('defect_type') or f.defect_guess}"
                          f"{', ' + f.note['severity'] if f.note and f.note.get('severity') else ''})"
                          for f in sm.flags) or "none yet"
        return (f"The drone is in state {sm.state} at {tel['x']:.0f} m of the {self.cfg.length:.0f} m corridor, "
                f"battery {sm.battery:.0f}%, {len(self.photos)} photos taken. Flags so far: {flags}.")

    # ------------------------------------------------------------ records
    def _save(self, kind: str, name: str, data: bytes, force=False):
        if not (self.save_frames or force):
            return None
        p = self.out / "media" / kind / name
        p.write_bytes(data)
        return str(p.relative_to(self.out))

    def _dec(self, dec, kind: str) -> dict:
        d = {"kind": kind, "ok": dec.ok, "action": dec.action, "probs": dec.probs, "confidence": dec.confidence,
             "sure": round(dec.sure, 3), "damage": round(dec.damage, 3), "defect": dec.defect,
             "nouls": {k: round(v, 3) for k, v in dec.nouls.items()}, "latency_ms": dec.latency_ms,
             "error": dec.error}
        self.decisions.append(d)
        return d

    @staticmethod
    def _g(g: Gated | None) -> dict | None:
        if g is None:
            return None
        return {"action": g.action, "source": g.label, "reason": g.reason, "weighted": g.weighted}

    # ------------------------------------------------------------ run
    def run(self, max_ticks: int = 3000, script: dict | None = None, hooks=()) -> dict:
        """script: {tick: command} operator commands injected at given ticks (tests stand in for voice).
        hooks: callables run with the mission before each tick (the voice script uses one)."""
        t0 = time.time()
        self.started = True
        self.emit("start", spec={k: self.spec[k] for k in ("kind", "seed", "length", "spacing", "pylons", "trees")
                                 if k in self.spec},
                  defects=self.spec["defects"], config=self.cfg.__dict__)
        while self.sm.state != "DONE" and self.ticks < max_ticks:
            if script and self.ticks in script:
                self.command(script[self.ticks])
            for h in hooks:
                h(self)
            self.tick()
        if self.escalator:
            self.emit("state", state=self.sm.state, reason=f"waiting for {len(self.escalator.futures)} notes")
            self.escalator.drain()
        summary = self.summary(time.time() - t0)
        self.emit("summary", **summary)
        (self.out / "summary.json").write_text(json.dumps(summary, indent=1))
        self.sim.close()
        return summary

    def summary(self, wall: float) -> dict:
        sm = self.sm
        lat = sorted(d["latency_ms"] for d in self.decisions if d["ok"])
        n = len(self.decisions)
        matched, false_alarms = {}, []
        for f in sm.flags:
            hit = next((d for d in self.spec["defects"]
                        if abs(d["x"] - f.target.x) <= 8 and abs(d["y"] - f.target.y) < 2), None)
            if hit:
                matched.setdefault(hit["id"], f.id)
            else:
                false_alarms.append(f.id)
        defects = self.spec["defects"]
        src = {}
        for line in (self.out / "mission.jsonl").read_text().splitlines() if (self.out / "mission.jsonl").exists() else []:
            ev = json.loads(line)
            if ev["type"] == "tick" and ev.get("gated"):
                src[ev["gated"]["source"]] = src.get(ev["gated"]["source"], 0) + 1
        return {
            "ticks": self.ticks, "sim_time_s": round(self.sim.t, 1), "wall_time_s": round(wall, 1),
            "realtime_factor": round(self.sim.t / wall, 2) if wall else None,
            "corridor_complete": sm.corridor_done, "returned_home": sm.state == "DONE",
            "return_reason": sm.return_reason, "battery_end": round(sm.battery, 1),
            "distance_m": round(self.sim.odometer, 1),
            "decisions": n, "decisions_ok": len(lat), "decision_sources": src,
            "latency_ms": {"median": statistics.median(lat) if lat else None,
                           "p90": lat[int(0.9 * (len(lat) - 1))] if lat else None, "max": lat[-1] if lat else None},
            "llm_calls": self.escalator.calls if self.escalator else 0,
            "llm_frame_fraction": round((self.escalator.calls if self.escalator else 0) / n, 4) if n else None,
            "notes_ok": sum(1 for f in sm.flags if f.note and not f.note.get("error")),
            "photos": len(self.photos), "flags": [{"id": f.id, "x": f.target.x, "y": f.target.y,
                                                   "guess": f.defect_guess, "source": f.source, "trigger": f.trigger,
                                                   "note": bool(f.note)} for f in sm.flags],
            "defects": len(defects), "defects_found": sorted(matched), "recall": round(len(matched) / len(defects), 3)
            if defects else None, "false_alarms": false_alarms,
        }


# ---------------------------------------------------------------- CLI
def add_args(p):
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--scene", default="m0", help="m0 (one broken insulator) or m2 (several defect types)")
    p.add_argument("--out", help="run directory (default runs/<timestamp>-fly)")
    p.add_argument("--fault-rate", type=float, default=0.0, help="drop this fraction of Clef decisions")
    p.add_argument("--clef-url", default=clef.URL)
    p.add_argument("--length", type=float, default=300.0)
    p.add_argument("--battery", type=float, default=100.0)
    p.add_argument("--max-ticks", type=int, default=3000)
    p.add_argument("--script", help='JSON {tick: command}, e.g. \'{"40": {"name": "return_home"}}\'')
    p.add_argument("--escalate", action="store_true", help="qwen38 writes a note for each flag (M2)")
    p.add_argument("--no-frames", action="store_true", help="do not save every cruise frame")
    p.add_argument("--lockstep", action="store_true", help="pause the world while the model thinks")
    p.add_argument("--speak", action="store_true", help="read each note and the summary aloud (Kokoro), WAVs saved")
    p.add_argument("--voice-script", help='JSON {"tick:N" or "flag:K": "fixtures/voice/x.wav"}: recorded commands '
                   "heard, routed by Clef and executed as if spoken")
    p.add_argument("--chase", action="store_true", help="also render the third-person chase camera each tick")


def scene(name: str, seed: int, length: float) -> dict:
    if name == "m0":
        return world.corridor_spec(seed, length=length)
    if name == "m2":
        return world.m2_spec(seed, length=length)
    raise SystemExit(f"unknown scene {name}")


def run_cli(a):
    out = Path(a.out or ROOT / "runs" / (time.strftime("%Y%m%d-%H%M%S") + "-fly"))
    out.mkdir(parents=True, exist_ok=True)
    spec = scene(a.scene, a.seed, a.length)
    (out / "scene.json").write_text(json.dumps(spec, indent=1))
    sink = JsonlSink(out / "mission.jsonl")

    def console(ev):
        if ev["type"] in ("state", "flag", "operator", "note", "voice", "speech", "answer"):
            print(json.dumps({k: v for k, v in ev.items() if k not in ("probs", "nouls")})[:300], flush=True)

    esc = None
    if a.escalate:
        from . import escalate
        esc = escalate.Escalator(length=a.length)
    m = Mission(spec, out, Config(length=a.length, battery_start=a.battery), clef_url=a.clef_url,
                fault_rate=a.fault_rate, seed=a.seed, sinks=[sink, console], escalator=esc,
                save_frames=not a.no_frames, realtime=not a.lockstep, chase=a.chase)
    script = {int(k): v for k, v in json.loads(a.script).items()} if a.script else None
    worker = speaker = vs = None
    hooks = []
    if a.speak or a.voice_script:
        from . import voice
        worker = voice.VoiceWorker()
        m.emit("voice_ready", **worker.ready)
        if a.speak:
            speaker = voice.Speaker(worker, out, publish=m.emit)
            m.sinks.append(speaker)
        if a.voice_script:
            vs = voice.VoiceScript(json.loads(a.voice_script), worker, speaker, a.clef_url)
            hooks.append(vs)
    try:
        s = m.run(a.max_ticks, script, hooks)
        if vs:
            vs.join()
        if speaker:
            speaker.drain()
    finally:
        if worker:
            worker.close()      # GPU.md: the speech models exit when the stage ends
    sink.close()
    s = m.summary(s["wall_time_s"])        # recount sources now the log is flushed
    (out / "summary.json").write_text(json.dumps(s, indent=1))
    print(json.dumps(s))
    print(f"run dir: {out}")
