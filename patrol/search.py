"""Direction 2, the search loop: sweep lanes -> anomaly finder -> Clef on each new crop -> gate -> investigate (fly
over the spot, descend stepwise, zoom close-up) -> Clef confirm -> alert -> resume the lane; RETURN on safety.

Ground truth stays out of the decision path. The mission sees rendered pixels and its own pose (what a real drone
knows from GPS, IMU and gimbal) and nothing else: after the Sim is built, the spec it keeps has no items, rocks or
trees, and `Sim.spec` is replaced with that public copy. Item positions go to `scene.json`, which only `score()` (after
the flight), the console's planted-items toggle and the tests read. tests/test_search.py enforces this.

Events (sinks, as in mission.py): start, tick, frame (finder boxes, ground positions, Clef odds per crop), state,
investigate, confirm (one per descent step), dismiss, alert, operator, summary.

usage: bin/patrol search --terrain snow --seed 0 --items blue_backpack,blue_tarp --clues blue_backpack [--out DIR]
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from . import anomaly, clef, clues as cluelib, geo, planner, world
from .mission import JsonlSink
from .sim import Sim

ROOT = Path(__file__).resolve().parents[1]
TRUTH_KEYS = ("items", "rocks", "trees", "defects")      # never on the decision path
SQUARE = [(-80.0, -80.0), (80.0, -80.0), (80.0, 80.0), (-80.0, 80.0)]


@dataclass
class SearchConfig:
    area: list = field(default_factory=lambda: list(SQUARE))
    home: tuple = (0.0, -95.0, 2.0)
    sweep_h: float | None = None     # None: the highest S0-backed height for the smallest clue (planner.sweep_height)
    overlap: float = 0.2             # cross-track overlap between lanes
    frame_every_m: float = 12.0      # along-track frame spacing (about half the 40 m footprint: every spot twice)
    speed: float = 6.0
    dt: float = 0.5
    W: int = 1280                    # sweep frame, the finder's input (S0: 1280x960 at 40 m)
    H: int = 960
    zoom_w: int = 512
    zoom_h: int = 384
    finder_k: int = 3
    steps: tuple = (20.0, 12.0)      # investigate heights, stepwise (S0: zoom at 20 m, then 12 m)
    t_confirm: float = 0.5           # clue noul to confirm (S0 separating range 0.05-0.69 at 20 m)
    t_dismiss: float = 0.2           # every clue noul below this at a step: dismiss without descending further
    inv_noul: float = 0.1            # sweep gate: investigate when any clue's noul on the crop reaches this
    inv_p: float = 0.9               # ... or when p(investigate) does (background crops: noul <= 0.052, p up to 0.81)
    judged_r: float = 3.0            # a candidate this close to an already judged spot is not asked again
    alert_r: float = 6.0             # a find this close to an alert of the same clue updates it (one alert per item)
    h_band: tuple = (8.0, 70.0)      # SAFETY: height above ground while searching
    area_margin: float = 25.0        # SAFETY: how far outside the area the drone may stray
    battery_s: float = 1200.0        # endurance, flight seconds
    reserve: float = 10.0            # battery % kept for landing
    clef_timeout: float = 6.0
    max_confirm_tries: int = 2


def outside_by(area, x: float, y: float) -> float:
    """0 inside the convex polygon, else the distance to it."""
    pts = np.asarray(area, float)
    n = len(pts)
    def cross(e, q):
        return e[0] * q[1] - e[1] * q[0]
    sign = [cross(pts[(i + 1) % n] - pts[i], np.array([x, y]) - pts[i]) for i in range(n)]
    if all(s >= 0 for s in sign) or all(s <= 0 for s in sign):
        return 0.0
    best = math.inf
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        t = np.clip(np.dot([x, y] - a, b - a) / max(np.dot(b - a, b - a), 1e-9), 0, 1)
        best = min(best, float(np.linalg.norm(a + t * (b - a) - [x, y])))
    return best


def polygon_area(area) -> float:
    pts = np.asarray(area, float)
    return float(abs(np.dot(pts[:, 0], np.roll(pts[:, 1], -1)) - np.dot(pts[:, 1], np.roll(pts[:, 0], -1))) / 2)


class SearchMission:
    def __init__(self, spec: dict, out: Path, clue_list: list[dict], cfg: SearchConfig | None = None,
                 clef_url: str = clef.URL, fault_rate: float = 0.0, seed: int = 0, sinks=(), save_frames: bool = True,
                 realtime: bool = True, chase: bool = False, ask=None):
        self.out = Path(out)
        for d in ("frames", "crops", "photos") + (("chase",) if chase else ()):
            (self.out / "media" / d).mkdir(parents=True, exist_ok=True)
        (self.out / "scene.json").write_text(json.dumps(spec))      # ground truth: scoring and console only
        self.cfg = cfg or SearchConfig()
        self.sim = Sim(spec, start=self.cfg.home)
        self.sim.CHASE_OFFSET, self.sim.CHASE_LOOK = (-12.0, -16.0, 9.0), (5.0, 8.0, -14.0)   # 3/4 view from above
        self.spec = {k: v for k, v in spec.items() if k not in TRUTH_KEYS}
        self.sim.spec = self.spec                                    # cut the simulator's copy of the truth too
        self.clues = clue_list
        self.sweep_h = self.cfg.sweep_h or planner.sweep_height([c["size_m"] for c in clue_list])
        self.lanes = planner.lanes(self.cfg.area, planner.lane_spacing(self.sweep_h, overlap=self.cfg.overlap))
        self.coverage = planner.Coverage(self.cfg.area)
        self.clef_url, self.fault_rate = clef_url, fault_rate
        self._ask_fn = ask or clef.ask
        self.rng = random.Random(seed + 202)
        self.sinks = list(sinks)
        self.save_frames, self.realtime, self.chase = save_frames, realtime, chase
        self.commands: deque = deque()
        self.state = "TAKEOFF"
        self.lane_i, self.on_lane = 0, False
        self.last_frame_xy: tuple | None = None
        self.resume_xy: tuple | None = None
        self.pending: list[dict] = []
        self.spot: dict | None = None
        self.judged: list[dict] = []          # every spot Clef has judged: {"g", "verdict"}
        self.investigated: list[dict] = []
        self.alerts: list[dict] = []
        self.decisions: list[dict] = []
        self.frames = self.ticks = 0
        self.flight_s = 0.0
        self.v_prev = (0.0, 0.0, 0.0)
        self.return_reason = ""
        self.started = False
        self.t_wall0 = time.time()

    # ------------------------------------------------------------ plumbing
    def emit(self, type_: str, **data):
        ev = {"type": type_, "t": round(self.sim.t, 2), **data}
        for s in self.sinks:
            s(ev)
        return ev

    def command(self, cmd: dict):
        self.commands.append(cmd)

    def _set(self, state: str, reason: str):
        self.state = state
        self.emit("state", state=state, reason=reason)

    def _save(self, kind: str, name: str, data: bytes, force=False):
        if not (self.save_frames or force):
            return None
        p = self.out / "media" / kind / name
        p.write_bytes(data)
        return str(p.relative_to(self.out))

    def _ask(self, jpeg: bytes, state: str, questions: dict, kind: str, h: float):
        if self.fault_rate and self.rng.random() < self.fault_rate:
            dec = clef.Decision(ok=False, error="injected fault: decision link dropped")
        else:
            dec = self._ask_fn(jpeg, state, questions, timeout=self.cfg.clef_timeout, url=self.clef_url)
        lat = dec.latency_ms / 1000.0
        if self.realtime and lat > 0:          # real-time honesty: the drone keeps flying its last command
            self._advance(self.v_prev, min(lat, 10.0))
        d = {"kind": kind, "ok": dec.ok, "action": dec.action, "probs": {k: round(v, 3) for k, v in dec.probs.items()},
             "nouls": {k: round(v, 3) for k, v in dec.nouls.items()}, "sure": round(dec.sure, 3),
             "latency_ms": dec.latency_ms, "error": dec.error, "h": round(float(self.sim.pos[2]), 1)}
        self.decisions.append(d)
        return dec, d

    def _advance(self, v, dt: float):
        self.sim.step(v, dt)
        if self.state not in ("DONE",):
            self.flight_s += dt

    def battery(self) -> float:
        return max(0.0, 100.0 * (1 - self.flight_s / self.cfg.battery_s))

    def _goto(self, goal, speed: float | None = None, gain: float = 0.6):
        """Velocity toward a point, slowing near it; True when there and nearly still."""
        p = self.sim.pos
        d = np.asarray(goal, float) - p
        dist = float(np.linalg.norm(d))
        s = min(speed or self.cfg.speed, gain * dist)
        v = d / dist * s if dist > 1e-6 else np.zeros(3)
        arrived = dist < 1.0 and float(np.linalg.norm(self.sim.vel)) < 0.6
        return tuple(float(x) for x in v), arrived

    # ------------------------------------------------------------ safety (code only; Clef never overrides it)
    def _safety(self) -> str | None:
        if self.state in ("RETURN", "DONE", "TAKEOFF"):
            return None
        x, y, z = (float(v) for v in self.sim.pos)
        lo, hi = self.cfg.h_band
        if not lo - 0.5 <= z <= hi + 0.5:
            return f"height {z:.1f} m outside the {lo:.0f}-{hi:.0f} m band"
        if outside_by(self.cfg.area, x, y) > self.cfg.area_margin:
            return f"more than {self.cfg.area_margin:.0f} m outside the search area"
        hx, hy, _ = self.cfg.home
        cost = 100.0 * (math.hypot(x - hx, y - hy) / self.cfg.speed + z / 2.0 + 20.0) / self.cfg.battery_s
        if self.battery() - cost < self.cfg.reserve:
            return f"battery {self.battery():.0f}% leaves only the return reserve"
        return None

    def _begin_return(self, why: str):
        self.return_reason = why
        self.pending.clear(); self.spot = None
        self._set("RETURN", why)

    # ------------------------------------------------------------ one tick
    def tick(self):
        cfg = self.cfg
        while self.commands:
            self._operator(self.commands.popleft())
        why = self._safety()
        if why:
            self._begin_return(why)
        v = (0.0, 0.0, 0.0)
        frame = None
        if self.state == "TAKEOFF":
            lane = self.lanes[0]
            if self.sim.pos[2] < self.sweep_h - 2:
                v = (0.0, 0.0, min(4.0, 0.8 * (self.sweep_h - float(self.sim.pos[2]))))
            else:
                v, arrived = self._goto((lane["x0"], lane["y"], self.sweep_h))
                if arrived:
                    self.on_lane = True
                    self._set("SWEEP", f"lane 1 of {len(self.lanes)} at {self.sweep_h:.0f} m")
        elif self.state == "SWEEP":
            lane = self.lanes[self.lane_i]
            if not self.on_lane:
                v, arrived = self._goto((lane["x0"], lane["y"], self.sweep_h))
                if arrived:
                    self.on_lane = True
                    self.last_frame_xy = None
            else:
                v, arrived = self._goto((lane["x1"], lane["y"], self.sweep_h))
                xy = (float(self.sim.pos[0]), float(self.sim.pos[1]))
                if self.last_frame_xy is None or math.dist(xy, self.last_frame_xy) >= cfg.frame_every_m or arrived:
                    frame = self._sweep_frame(lane)
                if self.state == "SWEEP" and arrived:
                    self.lane_i += 1
                    self.on_lane = False
                    if self.lane_i >= len(self.lanes):
                        self._begin_return("area covered")
                    else:
                        self.emit("state", state="SWEEP", reason=f"lane {self.lane_i + 1} of {len(self.lanes)}")
        elif self.state == "INVESTIGATE":
            s = self.spot
            v, arrived = self._goto((s["g"][0], s["g"][1], cfg.steps[s["step"]]))
            if arrived:
                self._confirm_step()
        elif self.state == "RESUME":
            lane = self.lanes[self.lane_i]
            v, arrived = self._goto((self.resume_xy[0], lane["y"], self.sweep_h))
            if arrived:
                self.last_frame_xy = self.resume_xy
                self._set("SWEEP", f"resumed lane {self.lane_i + 1} at x={self.resume_xy[0]:.0f}")
        elif self.state == "RETURN":
            hx, hy, hz = cfg.home
            if math.hypot(self.sim.pos[0] - hx, self.sim.pos[1] - hy) > 1.5:
                v, _ = self._goto((hx, hy, max(float(self.sim.pos[2]), 20.0)))
            else:
                v, arrived = self._goto((hx, hy, hz), speed=3.0)
                if arrived:
                    self._set("DONE", f"home ({self.return_reason})")
        rec = {"tick": self.ticks, "state": self.state, "tel": self.sim.telemetry(), "battery": round(self.battery(), 1),
               "lane": self.lane_i, "coverage": round(self.coverage.fraction(), 4), "frame": frame}
        if self.chase:
            rec["chase"] = self._save("chase", f"c{self.ticks:04d}.jpg", self.sim.jpeg("chase", 480, 360, quality=80),
                                      force=True)
        self.emit("tick", **rec)
        self._advance(v, cfg.dt)
        self.v_prev = v
        self.ticks += 1

    # ------------------------------------------------------------ sweep: finder -> Clef per new crop -> gate
    def _sweep_frame(self, lane: dict) -> str | None:
        cfg, sim = self.cfg, self.sim
        x, y = float(sim.pos[0]), float(sim.pos[1])
        heading = 1.0 if lane["x1"] >= lane["x0"] else -1.0
        sim.aim("inspect", (x + 0.3 * heading, y, 0.0))      # straight down, image up = direction of flight
        jpg = sim.jpeg("inspect", cfg.W, cfg.H, quality=90)
        pose = geo.camera_pose(sim, "inspect")
        foot = geo.frame_footprint(cfg.W, cfg.H, pose)
        if foot:
            self.coverage.mark(foot)
        self.last_frame_xy = (x, y)
        n = self.frames; self.frames += 1
        name = self._save("frames", f"f{n:04d}.jpg", jpg)
        h = float(sim.pos[2])
        cands = []
        for k, c in enumerate(anomaly.candidates(jpg, k=cfg.finder_k)):
            g = geo.pixel_to_ground(c["cx"], c["cy"], cfg.W, cfg.H, pose)
            row = {"box": [c["x0"], c["y0"], c["x1"], c["y1"]], "score": c["score"], "area": c["area"],
                   "g": [round(g[0], 2), round(g[1], 2)] if g else None}
            near = g and next((j for j in self.judged if math.dist(j["g"], g) < cfg.judged_r), None)
            if not g or near:
                row["status"] = "seen" if near else "off-ground"
                cands.append(row); continue
            crop = anomaly.crop(jpg, c)
            row["crop"] = self._save("crops", f"f{n:04d}_c{k}.jpg", crop, force=True)
            dec, d = self._ask(crop, cluelib.sweep_state(h), cluelib.sweep_schema(self.clues), "sweep", h)
            gate = self._sweep_gate(dec)
            row.update(status="judged", gate=gate, probs=d["probs"], nouls=d["nouls"], ms=d["latency_ms"])
            if dec.ok:        # a failed call leaves the spot unjudged, so a later frame may ask again
                self.judged.append({"g": g, "verdict": gate["action"]})
            if gate["action"] == "investigate" and not any(math.dist(s["g"], g) < cfg.alert_r
                                                           for s in self.pending + self.investigated):
                self.pending.append({"g": g, "clue": gate["clue"], "p_inv": gate["p_inv"], "noul": gate["noul"],
                                     "frame": name, "crop": row["crop"], "box": row["box"], "sweep_h": round(h, 1),
                                     "t_seen": round(sim.t, 2)})
            cands.append(row)
        self.emit("frame", n=n, frame=name, pose=pose, W=cfg.W, H=cfg.H, footprint=foot, candidates=cands,
                  coverage=round(self.coverage.fraction(), 4), lane=self.lane_i)
        if self.pending and self.state == "SWEEP":
            self.resume_xy = (float(sim.pos[0]), lane["y"])
            self._next_spot()
        return name

    def _sweep_gate(self, dec) -> dict:
        if not dec.ok:
            return {"action": "continue", "source": "FALLBACK", "why": dec.error, "clue": None, "noul": 0.0,
                    "p_inv": 0.0}
        p_inv = dec.probs.get("investigate", 0.0)
        best = max(self.clues, key=lambda c: dec.nouls.get(c["name"], 0.0))["name"]
        nb = dec.nouls.get(best, 0.0)
        inv = nb >= self.cfg.inv_noul or p_inv >= self.cfg.inv_p
        return {"action": "investigate" if inv else "continue", "source": "CLEF", "clue": best,
                "noul": round(nb, 3), "p_inv": round(p_inv, 3)}

    # ------------------------------------------------------------ investigate: fly over, descend, close-up, confirm
    def _next_spot(self):
        p = self.sim.pos
        self.pending.sort(key=lambda s: math.dist(s["g"], (p[0], p[1])))
        s = self.pending.pop(0)
        s.update(id=f"S{len(self.investigated) + 1}", step=0, tries=0, t_start=round(self.sim.t, 2), steps=[])
        self.spot = s
        self.investigated.append(s)
        self._set("INVESTIGATE", f"{s['id']}: maybe {s['clue']} at ({s['g'][0]:.0f}, {s['g'][1]:.0f}); "
                                 f"crop noul {s['noul']:.2f}, p(investigate) {s['p_inv']:.2f}")
        self.emit("investigate", spot={k: s[k] for k in ("id", "g", "clue", "p_inv", "noul", "frame", "crop", "box",
                                                         "sweep_h", "t_seen")})

    def _confirm_step(self):
        cfg, sim, s = self.cfg, self.sim, self.spot
        h = cfg.steps[s["step"]]
        self.state = "CONFIRM"
        sim.aim("zoom", (s["g"][0], s["g"][1], 0.0))
        jpg = sim.jpeg("zoom", cfg.zoom_w, cfg.zoom_h, quality=90)
        photo = self._save("photos", f"{s['id']}_{h:.0f}m.jpg", jpg, force=True)
        dec, d = self._ask(jpg, cluelib.confirm_state(h), cluelib.confirm_schema(self.clues), "confirm", h)
        verdict, clue, noul = self._confirm_gate(dec, last=s["step"] == len(cfg.steps) - 1)
        s["steps"].append({"h": h, "verdict": verdict, "clue": clue, "noul": noul, "choice": dec.action,
                           "photo": photo, "ms": d["latency_ms"]})
        self.emit("confirm", id=s["id"], h=h, verdict=verdict, clue=clue, noul=noul, choice=dec.action,
                  probs=d["probs"], nouls=d["nouls"], photo=photo, ok=dec.ok, ms=d["latency_ms"])
        self.state = "INVESTIGATE"
        if verdict == "closer":
            s["step"] += 1
            return
        if verdict == "unresolved":
            s["tries"] += 1
            if s["tries"] < cfg.max_confirm_tries:
                return
        s.update(verdict=verdict, t_end=round(sim.t, 2), h_final=h)
        if verdict == "confirm":
            self._alert(s, clue, noul, photo)
        else:
            self.emit("dismiss", id=s["id"], g=s["g"], verdict=verdict, h=h,
                      reason=f"{dec.action}; best clue noul {noul:.2f}" if dec.ok else dec.error)
        self.spot = None
        if self.state != "INVESTIGATE":
            return
        if self.pending:
            self._next_spot()
        elif self.resume_xy:
            self._set("RESUME", f"back to lane {self.lane_i + 1}")
        else:
            self._set("SWEEP", "back to the sweep")

    def _confirm_gate(self, dec, last: bool) -> tuple[str, str | None, float]:
        if not dec.ok:
            return "unresolved", None, 0.0
        names = [c["name"] for c in self.clues]
        best = max(names, key=lambda n: dec.nouls.get(n, 0.0))
        clue = dec.action if dec.action in names else best
        noul = round(dec.nouls.get(clue, 0.0), 3)
        if dec.action in names and noul >= self.cfg.t_confirm:
            return "confirm", clue, noul
        if dec.nouls.get(best, 0.0) < self.cfg.t_dismiss or last:
            return "dismiss", clue, noul
        return "closer", clue, noul

    def _alert(self, s: dict, clue: str, noul: float, photo: str):
        g = s["g"]
        dup = next((a for a in self.alerts if a["clue"] == clue and math.dist(a["g"], g) < self.cfg.alert_r), None)
        if dup:
            dup["seen"] += 1
            dup["conf"] = max(dup["conf"], noul)
            self.emit("dismiss", id=s["id"], g=g, verdict="duplicate", h=s["h_final"], reason=f"same as {dup['id']}")
            return
        fam = next(c["family"] for c in self.clues if c["name"] == clue)
        a = {"id": f"A{len(self.alerts) + 1}", "clue": clue, "family": fam, "g": [round(g[0], 2), round(g[1], 2)],
             "conf": noul, "h": s["h_final"], "photo": photo, "sweep_crop": s["crop"], "sweep_h": s["sweep_h"],
             "spot": s["id"], "t": round(self.sim.t, 2), "seen": 1}
        self.alerts.append(a)
        self.state = "ALERT"
        self.emit("alert", **a)
        self.state = "INVESTIGATE"

    # ------------------------------------------------------------ operator
    def _operator(self, cmd: dict):
        name = cmd.get("name")
        ok, why = False, "not applicable"
        if name == "return_home" and self.state not in ("RETURN", "DONE"):
            self._begin_return("operator: return home"); ok, why = True, ""
        elif name == "go_back_to_last_alert" and self.alerts and self.state in ("SWEEP", "RESUME"):
            a = self.alerts[-1]
            if self.state == "SWEEP":
                self.resume_xy = (float(self.sim.pos[0]), self.lanes[self.lane_i]["y"])
            self.pending.insert(0, {"g": tuple(a["g"]), "clue": a["clue"], "p_inv": 1.0, "noul": a["conf"],
                                    "frame": None, "crop": a["sweep_crop"], "box": None, "sweep_h": a["sweep_h"],
                                    "t_seen": round(self.sim.t, 2), "revisit": a["id"]})
            self._next_spot(); ok, why = True, ""
        self.emit("operator", command=cmd, accepted=ok, reason=why)

    def status_text(self) -> str:
        found = "; ".join(f"{a['id']} {a['family']} at ({a['g'][0]:.0f}, {a['g'][1]:.0f})" for a in self.alerts)
        return (f"State {self.state}, lane {min(self.lane_i + 1, len(self.lanes))} of {len(self.lanes)}, area searched "
                f"{100 * self.coverage.fraction():.0f}%, battery {self.battery():.0f}%. Alerts: {found or 'none yet'}.")

    # ------------------------------------------------------------ run
    def run(self, max_ticks: int = 4000, script: dict | None = None, hooks=(), pace: float = 0.0) -> dict:
        """pace > 0: sim time runs at most `pace` x wall-clock time (live console); 0: as fast as it computes."""
        t0 = time.time()
        self.started = True
        self.emit("start", spec=self.spec, clues=self.clues, config=asdict(self.cfg), sweep_h=self.sweep_h,
                  lanes=self.lanes, home=self.cfg.home)
        while self.state != "DONE" and self.ticks < max_ticks:
            if script and self.ticks in script:
                self.command(script[self.ticks])
            for h in hooks:
                h(self)
            self.tick()
            if pace > 0:
                ahead = self.sim.t / pace - (time.time() - t0)
                if ahead > 0:
                    time.sleep(min(ahead, 1.0))
        summary = self.summary(time.time() - t0)
        self.emit("summary", **summary)
        (self.out / "summary.json").write_text(json.dumps(summary, indent=1))
        self.sim.close()
        return summary

    def summary(self, wall: float) -> dict:
        def stats(ds):
            lat = sorted(d["latency_ms"] for d in ds if d["ok"])
            return {"n": len(ds), "ok": len(lat), "median_ms": round(statistics.median(lat)) if lat else None,
                    "p90_ms": round(lat[int(0.9 * (len(lat) - 1))]) if lat else None}
        sweep = [d for d in self.decisions if d["kind"] == "sweep"]
        conf = [d for d in self.decisions if d["kind"] == "confirm"]
        inv = [s for s in self.investigated if "verdict" in s]
        used = 100.0 - self.battery()
        area_m2 = round(self.coverage.fraction() * polygon_area(self.cfg.area))
        return {"state": self.state, "return_reason": self.return_reason, "sim_s": round(self.sim.t, 1),
                "wall_s": round(wall, 1), "flight_s": round(self.flight_s, 1), "battery_used_pct": round(used, 1),
                "sweep_h": self.sweep_h, "lanes": len(self.lanes), "lanes_done": min(self.lane_i, len(self.lanes)),
                "coverage": round(self.coverage.fraction(), 4), "area_m2_covered": area_m2,
                "frames": self.frames, "clef_sweep": stats(sweep), "clef_confirm": stats(conf),
                "fallback": sum(not d["ok"] for d in self.decisions),
                "investigations": len(inv), "dismissed": sum(s["verdict"] != "confirm" for s in inv),
                "mean_investigate_s": round(statistics.mean(s["t_end"] - s["t_start"] for s in inv), 1) if inv else None,
                "mean_decision_h": round(statistics.mean(s["h_final"] for s in inv), 1) if inv else None,
                "alerts": self.alerts, "time_to_first_alert": self.alerts[0]["t"] if self.alerts else None}


# ---------------------------------------------------------------- scenes and scoring (ground truth lives here)
def item_info(name: str) -> dict:
    if name in world.PRIMS:
        geoms, size = world.PRIMS[name]
        return {"prim": name, "obj": None, "texture": None, "size_m": size,
                "extent_m": [size, size, round(max(g[4] for g in geoms) * 2, 2)]}
    p = ROOT / "assets" / "items" / name / "mujoco" / "mujoco.json"
    if not p.exists():
        raise SystemExit(f"item {name} is not built: {p} missing (tools/build_items.sh)")
    return json.loads(p.read_text())


def build_scene(terrain: str, seed: int, names: list[str], clue_names: list[str], area=SQUARE,
                home=(0.0, -95.0), min_sep: float = 30.0) -> dict:
    """Place the named items at seeded positions inside the area (inset 12 m, apart, away from home)."""
    rng = random.Random(seed * 977 + 13)
    xs, ys = [p[0] for p in area], [p[1] for p in area]
    placed = []
    for name in names:
        info = item_info(name)
        for _ in range(500):
            x, y = rng.uniform(min(xs) + 12, max(xs) - 12), rng.uniform(min(ys) + 12, max(ys) - 12)
            if all(math.dist((x, y), (q["x"], q["y"])) >= min_sep for q in placed) and math.dist((x, y), home) > 30:
                break
        placed.append({"name": name, "role": "clue" if name in clue_names else "decoy", "prim": info.get("prim"),
                       "obj": info["obj"],
                       "texture": info["texture"], "x": round(x, 2), "y": round(y, 2),
                       "yaw": round(rng.uniform(0, 360), 1), "h": info["extent_m"][2], "size_m": info["size_m"]})
    size = 2 * (max(max(map(abs, xs)), max(map(abs, ys))) + 20)
    return world.search_spec(seed, terrain, placed, size=size)


def score(out: Path, match_r: float = 5.0) -> dict:
    """After the flight: compare alerts and frames with the planted items (scene.json). Scoring only."""
    out = Path(out)
    scene = json.loads((out / "scene.json").read_text())
    evs = [json.loads(l) for l in (out / "mission.jsonl").read_text().splitlines()]
    frames = [e for e in evs if e["type"] == "frame"]
    alerts = [e for e in evs if e["type"] == "alert"]
    invs = [e["spot"] for e in evs if e["type"] == "investigate"]
    rows = []
    for it in scene["items"]:
        p = (it["x"], it["y"])
        seen = noticed = 0
        for f in frames:
            uv = geo.ground_to_pixel(p[0], p[1], f["W"], f["H"], f["pose"])
            if uv:
                seen += 1
                noticed += any(c["box"][0] - 4 <= uv[0] <= c["box"][2] + 4 and c["box"][1] - 4 <= uv[1] <= c["box"][3] + 4
                               for c in f["candidates"])
        inv = [s for s in invs if math.dist(s["g"], p) < match_r]
        al = [a for a in alerts if math.dist(a["g"], p) < match_r]
        rows.append({"name": it["name"], "role": it["role"], "xy": p, "frames_in_view": seen, "noticed": noticed,
                     "investigated": len(inv), "alerts": [a["id"] for a in al],
                     "right_clue": any(a["clue"] == it["name"] for a in al),
                     "loc_err_m": round(min(math.dist(a["g"], p) for a in al), 2) if al else None,
                     "t_alert": min(a["t"] for a in al) if al else None})
    clue_rows = [r for r in rows if r["role"] == "clue"]
    true_ids = {i for r in clue_rows if r["right_clue"] for i in r["alerts"]}
    false_alerts = [a["id"] for a in alerts if a["id"] not in true_ids]
    found = [r for r in clue_rows if r["right_clue"]]
    return {"items": rows, "recall": f"{len(found)}/{len(clue_rows)}", "found": len(found), "clues": len(clue_rows),
            "false_alerts": false_alerts, "decoys_investigated": sum(r["investigated"] > 0 for r in rows
                                                                    if r["role"] == "decoy"),
            "loc_err_m": [r["loc_err_m"] for r in found],
            "time_to_first_find": min((r["t_alert"] for r in found), default=None)}


def add_args(ap: argparse.ArgumentParser):
    ap.add_argument("--terrain", default="snow", choices=sorted(world.TERRAINS))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--items", default="blue_backpack,blue_tarp", help="items placed in the scene")
    ap.add_argument("--clues", default="blue_backpack", help="what the family described (catalogue names)")
    ap.add_argument("--out")
    ap.add_argument("--sweep-h", type=float)
    ap.add_argument("--half", type=float, default=80.0, help="half-width of the square search area, m")
    ap.add_argument("--clef-url", default=clef.URL)
    ap.add_argument("--fault-rate", type=float, default=0.0)
    ap.add_argument("--lockstep", action="store_true", help="pause the world while Clef thinks")
    ap.add_argument("--chase", action="store_true", help="render the chase camera every tick (console, video)")
    ap.add_argument("--pace", type=float, default=0.0, help="sim seconds per wall second (0: as fast as possible)")
    ap.add_argument("--max-ticks", type=int, default=4000)


def make_mission(a, out: Path, sinks=()) -> SearchMission:
    """The scene and mission for parsed add_args() options (the CLI and the console both use this)."""
    names = [n for n in a.items.split(",") if n]
    cnames = [n for n in a.clues.split(",") if n]
    h = a.half
    cfg = SearchConfig(area=[(-h, -h), (h, -h), (h, h), (-h, h)], home=(0.0, -h - 15, 2.0), sweep_h=a.sweep_h)
    spec = build_scene(a.terrain, a.seed, names, cnames, area=cfg.area, home=cfg.home[:2])
    return SearchMission(spec, out, cluelib.clues(cnames), cfg, clef_url=a.clef_url, fault_rate=a.fault_rate,
                         seed=a.seed, sinks=sinks, realtime=not a.lockstep, chase=a.chase)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="patrol search")
    add_args(ap)
    a = ap.parse_args(argv)
    out = Path(a.out or ROOT / "runs" / time.strftime("%Y%m%d-%H%M%S-search"))
    out.mkdir(parents=True, exist_ok=True)
    sink = JsonlSink(out / "mission.jsonl")
    m = make_mission(a, out, [sink])
    s = m.run(max_ticks=a.max_ticks, pace=a.pace)
    sink.close()
    sc = score(out)
    (out / "score.json").write_text(json.dumps(sc, indent=1))
    print(json.dumps({k: s[k] for k in ("state", "return_reason", "sim_s", "wall_s", "coverage", "frames",
                                        "investigations", "dismissed")} | {"alerts": [(x["id"], x["clue"]) for x in
                                                                                     s["alerts"]]}))
    print(json.dumps({k: sc[k] for k in ("recall", "false_alerts", "decoys_investigated", "loc_err_m",
                                         "time_to_first_find")}))
    print(f"run: {out}")


if __name__ == "__main__":
    main()
