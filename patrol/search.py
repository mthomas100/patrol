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
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from . import anomaly, clef, clues as cluelib, geo, planner, thinker, world
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
    frame_every_m: float | None = None   # along-track frame spacing; None: planner.frame_spacing (12 m at 40 m, half
    #                                     the frame below it, every spot about twice; DECISIONS 14:55)
    clue_margin: float = 1.2         # lane overlap and frame spacing leave room for the largest clue times this
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
    inv_noul_weak: float = 0.05      # ... or when both agree weakly: a tent crop at noul 0.094, p 0.755 was missed;
    inv_p_weak: float = 0.7          #     on 1384 tuning background crops this adds none (DECISIONS 13:15)
    judged_r: float = 3.0            # a candidate this close to an already judged spot is not asked again ...
    rejudge_gain: float = 2.0        # ... unless its box is this many times larger (a far-edge glimpse judged first
    max_asks: int = 3                #     must not hide the clear view a lane later; runs/s3-trail-ab-rt grass6)
    edge_px: int = 8                 # boxes this close to the frame edge wait for a neighbouring frame (overlap)
    alert_r: float = 6.0             # a find this close to an alert of the same clue updates it (one alert per item)
    h_band: tuple = (8.0, 70.0)      # SAFETY: height above ground while searching
    area_margin: float = 25.0        # SAFETY: how far outside the area the drone may stray
    battery_s: float = 1800.0        # endurance, flight seconds: 30 min, what a 40-45 min SAR drone keeps in the cold
    #                                  (was 1,200 s until 15:55; scenario 5 ran out at 21.8 m in 3 of 3; DECISIONS 15:55)
    reserve: float = 10.0            # battery % kept for landing
    clef_timeout: float = 6.0
    max_confirm_tries: int = 2
    sector_len: float = 40.0         # lanes are cut into sectors the slow thinker can reorder
    oblique: float = 0.6             # investigate hover offset = oblique x height (about 31 degrees off vertical)
    zoom_foot_min: float = 4.0       # zoom framing: ground height of the close-up, at least this many metres ...
    zoom_frame: float = 3.0          # ... and this many times the suspected clue's size
    thinker: bool = False            # qwen38 on board: notes, trail reasoning, second opinions (S3)
    trail: bool = True               # with the thinker: reorder sectors after a find
    second: bool = True              # with the thinker: second opinion on close calls at the lowest step
    second_min: float = 0.6          # qwen38 confidence needed to confirm a close call


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
        big = self.cfg.clue_margin * max((c["size_m"] for c in clue_list), default=0.0)
        self.lane_spacing = planner.lane_spacing(self.sweep_h, overlap=self.cfg.overlap, min_overlap_m=big)
        self.frame_every = self.cfg.frame_every_m or planner.frame_spacing(self.sweep_h, clue_m=big)
        self.lanes = planner.lanes(self.cfg.area, self.lane_spacing)
        self.sectors = planner.sectors(self.lanes, self.cfg.sector_len)
        self.queue = list(range(len(self.sectors)))     # sector indices still to sweep, in order
        self.done_sectors: list[str] = []
        self.cur: dict | None = None                    # the sector being swept, oriented in flying direction
        self.on_sector = False
        self.worker = thinker.Worker() if self.cfg.thinker else None
        self.plan_next: dict | None = None              # a validated trail plan waiting for the sector to end
        self.plans: list[dict] = []
        self.calls0 = dict(thinker.CALLS)
        self.coverage = planner.Coverage(self.cfg.area)
        self.clef_url, self.fault_rate = clef_url, fault_rate
        self._ask_fn = ask or clef.ask
        self.rng = random.Random(seed + 202)
        self.sinks = list(sinks)
        self.save_frames, self.realtime, self.chase = save_frames, realtime, chase
        self.commands: deque = deque()
        self.state = "TAKEOFF"
        self.lane_i = 0
        self.last_frame_xy: tuple | None = None
        self.resume_xy: tuple | None = None
        self.pending: list[dict] = []
        self.spot: dict | None = None
        self.judged: list[dict] = []          # every spot Clef has judged: {"g", "verdict", "area", "asks"}
        self.investigated: list[dict] = []
        self.alerts: list[dict] = []
        self.decisions: list[dict] = []
        self.frames = self.ticks = self.n_cands = 0
        self.flight_s = 0.0
        self.state_s: dict = defaultdict(float)          # flight seconds and metres per state (the plan guard's rates)
        self.state_m: dict = defaultdict(float)
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
        qa = thinker.ACTIVE.is_set()
        if self.fault_rate and self.rng.random() < self.fault_rate:
            dec = clef.Decision(ok=False, error="injected fault: decision link dropped")
        else:
            dec = self._ask_fn(jpeg, state, questions, timeout=self.cfg.clef_timeout, url=self.clef_url)
        qa = qa or thinker.ACTIVE.is_set()
        lat = dec.latency_ms / 1000.0
        if self.realtime and lat > 0:          # real-time honesty: the drone keeps flying its last command
            self._advance(self.v_prev, min(lat, 10.0))
        d = {"kind": kind, "ok": dec.ok, "action": dec.action, "probs": {k: round(v, 3) for k, v in dec.probs.items()},
             "nouls": {k: round(v, 3) for k, v in dec.nouls.items()}, "sure": round(dec.sure, 3),
             "latency_ms": dec.latency_ms, "error": dec.error, "h": round(float(self.sim.pos[2]), 1),
             "qwen_active": qa}
        self.decisions.append(d)
        return dec, d

    def _advance(self, v, dt: float):
        o = self.sim.odometer
        self.sim.step(v, dt)
        if self.state not in ("DONE",):
            self.flight_s += dt
            self.state_s[self.state] += dt
            self.state_m[self.state] += self.sim.odometer - o

    def battery(self) -> float:
        return max(0.0, 100.0 * (1 - self.flight_s / self.cfg.battery_s))

    def _goto(self, goal, speed: float | None = None, gain: float = 0.6, stop: bool = True):
        """Velocity toward a point, slowing near it; True when there and nearly still (stop=False: fly through it
        at speed, there when within a tick's travel)."""
        p = self.sim.pos
        d = np.asarray(goal, float) - p
        dist = float(np.linalg.norm(d))
        s = min(speed or self.cfg.speed, gain * dist) if stop else (speed or self.cfg.speed)
        v = d / dist * s if dist > 1e-6 else np.zeros(3)
        if not stop:
            return tuple(float(x) for x in v), dist < s * self.cfg.dt + 0.5
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
        cost = 100.0 * self._return_s((x, y), z) / self.cfg.battery_s
        if self.battery() - cost < self.cfg.reserve:
            return f"battery {self.battery():.0f}% leaves only the return reserve"
        return None

    def _return_s(self, xy, z: float) -> float:
        """Flight seconds to get home and land from (x, y) at height z."""
        hx, hy, _ = self.cfg.home
        return math.hypot(xy[0] - hx, xy[1] - hy) / self.cfg.speed + z / 2.0 + 20.0

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
            if self.sim.pos[2] < self.sweep_h - 2:
                v = (0.0, 0.0, min(4.0, 0.8 * (self.sweep_h - float(self.sim.pos[2]))))
            else:
                self._set("SWEEP", f"sector {self.sectors[self.queue[0]]['id']} of {len(self.sectors)} at "
                                   f"{self.sweep_h:.0f} m")
                self._begin_sector()
        elif self.state == "SWEEP":
            sec = self.cur
            if not self.on_sector:
                v, arrived = self._goto((sec["x0"], sec["y"], self.sweep_h))
                if arrived:
                    self.on_sector = True
                    self.last_frame_xy = None
            else:
                cont = self._continues()
                v, arrived = self._goto((sec["x1"], sec["y"], self.sweep_h), stop=not cont)
                xy = (float(self.sim.pos[0]), float(self.sim.pos[1]))
                if self.last_frame_xy is None or math.dist(xy, self.last_frame_xy) >= self.frame_every or \
                        (arrived and not cont):
                    frame = self._sweep_frame(sec)
                if self.state == "SWEEP" and arrived:
                    self._end_sector()
        elif self.state == "INVESTIGATE":
            s = self.spot
            h = cfg.steps[s["step"]]
            u = s["approach"]          # hover short of the spot on the approach side: an oblique, not top-down, look
            v, arrived = self._goto((s["g"][0] + u[0] * cfg.oblique * h, s["g"][1] + u[1] * cfg.oblique * h, h))
            if arrived:
                self._confirm_step()
        elif self.state == "RESUME":
            v, arrived = self._goto((self.resume_xy[0], self.resume_xy[1], self.sweep_h))
            if arrived:
                self.last_frame_xy = self.resume_xy
                self.on_sector = True
                self._set("SWEEP", f"resumed sector {self.cur['id']} at x={self.resume_xy[0]:.0f}")
        elif self.state == "RETURN":
            hx, hy, hz = cfg.home
            if math.hypot(self.sim.pos[0] - hx, self.sim.pos[1] - hy) > 1.5:
                v, _ = self._goto((hx, hy, max(float(self.sim.pos[2]), 20.0)))
            else:
                v, arrived = self._goto((hx, hy, hz), speed=3.0)
                if arrived:
                    self._set("DONE", f"home ({self.return_reason})")
        rec = {"tick": self.ticks, "state": self.state, "tel": self.sim.telemetry(), "battery": round(self.battery(), 1),
               "lane": self.lane_i, "sector": self.cur["id"] if self.cur else None,
               "coverage": round(self.coverage.fraction(), 4), "frame": frame}
        if self.chase:
            rec["chase"] = self._save("chase", f"c{self.ticks:04d}.jpg", self.sim.jpeg("chase", 480, 360, quality=80),
                                      force=True)
        self.emit("tick", **rec)
        self._advance(v, cfg.dt)
        self.v_prev = v
        self.ticks += 1

    # ------------------------------------------------------------ sectors
    def _begin_sector(self):
        """Take the next sector in the queue, flown from whichever end is nearer."""
        if not self.queue:
            self.cur = None
            return self._begin_return("area covered")
        sec = dict(self.sectors[self.queue[0]])
        p = (float(self.sim.pos[0]), float(self.sim.pos[1]))
        if math.dist(p, (sec["x1"], sec["y"])) < math.dist(p, (sec["x0"], sec["y"])):
            sec["x0"], sec["x1"] = sec["x1"], sec["x0"]
        self.cur, self.lane_i = sec, sec["lane"]
        self.on_sector = math.dist(p, (sec["x0"], sec["y"])) < 3.0 and abs(float(self.sim.pos[2]) - self.sweep_h) < 2

    def _continues(self) -> bool:
        """The next sector starts where this one ends and runs on in the same direction: fly through, no stop."""
        if len(self.queue) < 2 or self.plan_next:
            return False
        nxt, c = self.sectors[self.queue[1]], self.cur
        same_way = (nxt["x1"] - nxt["x0"]) * (c["x1"] - c["x0"]) > 0
        return abs(nxt["y"] - c["y"]) < 0.5 and abs(nxt["x0"] - c["x1"]) < 0.5 and same_way

    def _end_sector(self):
        self.done_sectors.append(self.sectors[self.queue.pop(0)]["id"])
        if self.plan_next:
            self._apply_plan()
        self._begin_sector()

    def _apply_plan(self):
        p, self.plan_next = self.plan_next, None
        ids = {self.sectors[i]["id"]: i for i in self.queue}
        first = [ids[x] for x in p["first"] if x in ids]
        refused = ""
        if first:      # the plan's sectors in its order, then the rest nearest first from where they end
            rest = [i for i in self.queue if i not in first]
            end = planner.route_m([self.sectors[i] for i in first], self.sim.pos[:2])[1]
            new = first + [rest[j] for j in planner.nearest_first([self.sectors[i] for i in rest], end)]
            refused = self._unaffordable(new)
            if not refused:
                self.queue = new
        self.emit("plan", applied=not refused, first=[self.sectors[i]["id"] for i in first], reason=p.get("reason", ""),
                  **({"refused": refused} if refused else {}))

    def _unaffordable(self, new: list[int]) -> str:
        """Code owns the route: a trail plan may reorder the sweep but not cost the area. Refuse it when the battery
        can fly the current order to the end and not the new one; when neither fits, the likelier sectors go first.
        Time per metre of sweep and the detours per sweep second are this flight's own so far (DECISIONS 14:55)."""
        sweep_s = self.state_s["SWEEP"]
        v = self.state_m["SWEEP"] / sweep_s if sweep_s > 30 else 0.6 * self.cfg.speed
        detour = (self.state_s["INVESTIGATE"] + self.state_s["RESUME"]) / sweep_s if sweep_s > 30 else 0.0
        left = (self.battery() - self.cfg.reserve) / 100.0 * self.cfg.battery_s

        def need(order):
            m, end = planner.route_m([self.sectors[i] for i in order], self.sim.pos[:2])
            return m / max(v, 0.5) * (1 + detour) + self._return_s(end, self.sweep_h)
        t_new, t_old = need(new), need(self.queue)
        if t_new > left >= t_old:
            return (f"battery: the reordered sweep needs about {t_new:.0f} s and {left:.0f} s are left; the current "
                    f"order needs {t_old:.0f} s")
        return ""

    # ------------------------------------------------------------ sweep: finder -> Clef per new crop -> gate
    def _sweep_frame(self, lane: dict) -> str | None:
        """One sweep photo over the current sector (`lane` is the sector dict, oriented in flying direction)."""
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
        found = anomaly.candidates(jpg, k=cfg.finder_k)
        self.n_cands += len(found)
        for k, c in enumerate(found):
            g = geo.pixel_to_ground(c["cx"], c["cy"], cfg.W, cfg.H, pose)
            row = {"box": [c["x0"], c["y0"], c["x1"], c["y1"]], "score": c["score"], "area": c["area"],
                   "g": [round(g[0], 2), round(g[1], 2)] if g else None}
            near = g and next((j for j in self.judged if math.dist(j["g"], g) < cfg.judged_r), None)
            if near and c["area"] >= cfg.rejudge_gain * near["area"] and near["asks"] < cfg.max_asks:
                row["rejudge"] = {"was": near["verdict"], "area_was": near["area"]}
                near = None               # a much better view of a spot judged from a poor one: ask again
            # A box cut by the frame edge is judged now, not left for a neighbouring frame: on 20 tuning flights 558 of
            # 960 deferred edge boxes were never judged from any frame (DECISIONS 13:29). A later, much larger view of
            # the same spot is asked again (rejudge_gain), so a cut first view does not hide the whole object.
            if min(c["x0"], c["y0"], cfg.W - c["x1"], cfg.H - c["y1"]) <= cfg.edge_px:
                row["edge"] = True
            if not g or near:
                row["status"] = "seen" if near else "off-ground"
                cands.append(row); continue
            crop = anomaly.crop(jpg, c)
            row["crop"] = self._save("crops", f"f{n:04d}_c{k}.jpg", crop, force=True)
            dec, d = self._ask(crop, cluelib.sweep_state(h), cluelib.sweep_schema(self.clues), "sweep", h)
            gate = self._sweep_gate(dec)
            row.update(status="judged", gate=gate, probs=d["probs"], nouls=d["nouls"], ms=d["latency_ms"])
            if dec.ok:        # a failed call leaves the spot unjudged, so a later frame may ask again
                old = next((j for j in self.judged if math.dist(j["g"], g) < cfg.judged_r), None)
                if old:
                    old.update(g=g, verdict=gate["action"], area=c["area"], asks=old["asks"] + 1)
                else:
                    self.judged.append({"g": g, "verdict": gate["action"], "area": c["area"], "asks": 1})
            # a spot already waiting blocks within judged_r; one already flown blocks only the ground its close-ups
            # covered (a background spot framed for a backpack hid the tent 3.8 m away: runs/s5-live-test1)
            if gate["action"] == "investigate" and not any(
                    math.dist(s["g"], g) < s.get("cover_r", cfg.judged_r) for s in self.pending + self.investigated):
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
        inv = nb >= self.cfg.inv_noul or p_inv >= self.cfg.inv_p or \
            (nb >= self.cfg.inv_noul_weak and p_inv >= self.cfg.inv_p_weak)
        return {"action": "investigate" if inv else "continue", "source": "CLEF", "clue": best,
                "noul": round(nb, 3), "p_inv": round(p_inv, 3)}

    # ------------------------------------------------------------ investigate: fly over, descend, close-up, confirm
    def _next_spot(self):
        p = self.sim.pos
        self.pending.sort(key=lambda s: (not s.get("revisit"), math.dist(s["g"], (p[0], p[1]))))   # operator's first
        s = self.pending.pop(0)
        d = np.array([p[0] - s["g"][0], p[1] - s["g"][1]])
        n = float(np.linalg.norm(d))
        s.update(id=f"S{len(self.investigated) + 1}", step=0, tries=0, t_start=round(self.sim.t, 2), steps=[],
                 approach=(d / n).tolist() if n > 1e-6 else [0.0, -1.0])
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
        size = next((c["size_m"] for c in self.clues if c["name"] == s["clue"]), 1.0)
        foot = max(cfg.zoom_foot_min, cfg.zoom_frame * size)
        slant = math.dist(tuple(float(v) for v in sim.pos), (s["g"][0], s["g"][1], 0.0))
        fovy = min(24.0, max(3.0, math.degrees(2 * math.atan(foot / 2 / max(slant, 1.0)))))
        sim.model.cam_fovy[sim.cam["zoom"]] = fovy       # a zoom lens framed to the suspected clue's size
        s["cover_r"] = max(cfg.judged_r, foot / 2)       # the ground this close-up checked, for the sweep's dedupe
        sim.aim("zoom", (s["g"][0], s["g"][1], 0.0))
        jpg = sim.jpeg("zoom", cfg.zoom_w, cfg.zoom_h, quality=90)
        photo = self._save("photos", f"{s['id']}_{h:.0f}m.jpg", jpg, force=True)
        dec, d = self._ask(jpg, cluelib.confirm_state(h), cluelib.confirm_schema(self.clues), "confirm", h)
        verdict, clue, noul = self._confirm_gate(dec, last=s["step"] == len(cfg.steps) - 1)
        s["steps"].append({"h": h, "verdict": verdict, "clue": clue, "noul": noul, "choice": dec.action,
                           "photo": photo, "ms": d["latency_ms"]})
        self.emit("confirm", id=s["id"], h=h, verdict=verdict, clue=clue, noul=noul, choice=dec.action,
                  probs=d["probs"], nouls=d["nouls"], photo=photo, ok=dec.ok, ms=d["latency_ms"],
                  zoom_fovy=round(fovy, 1), slant_m=round(slant, 1))
        self.state = "INVESTIGATE"
        if verdict == "closer":
            s["step"] += 1
            return
        if verdict == "unresolved":
            s["tries"] += 1
            if s["tries"] < cfg.max_confirm_tries:
                return
        if verdict == "uncertain":
            verdict, clue, noul = self._second_opinion(s, clue, noul, jpg)
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
        unsure = dec.action in names or dec.nouls.get(best, 0.0) >= self.cfg.t_dismiss   # choice and nouls disagree
        if not unsure:
            return "dismiss", clue, noul
        return ("uncertain" if last else "closer"), clue, noul

    def _second_opinion(self, s: dict, clue: str, noul: float, jpg: bytes) -> tuple[str, str, float]:
        """A close call at the lowest step: Clef chose a clue but its noul stayed under t_confirm (or the reverse).
        Without the slow thinker that is a dismissal (no alert without corroboration); with it, qwen38 looks at the
        same close-up and sweep crop while the drone hovers, and the alert says it was confirmed by both."""
        if not (self.worker and self.cfg.second):
            return "dismiss", clue, noul
        c = next(c for c in self.clues if c["name"] == clue)
        crop = (self.out / s["crop"]).read_bytes() if s.get("crop") else None
        t0 = time.time()
        r = thinker.second_opinion(c, s["steps"][-1]["h"], s["sweep_h"], jpg, crop)
        if self.realtime:
            self._advance((0.0, 0.0, 0.0), min(time.time() - t0, 30.0))     # hovering while qwen38 looks
        ok = bool(r.get("is_clue")) and float(r.get("confidence", 0.0)) >= self.cfg.second_min
        self.emit("second_opinion", id=s["id"], clue=clue, clef_noul=noul, verdict="confirm" if ok else "dismiss", **r)
        if ok:
            s["by"] = "Clef + qwen38"
        return ("confirm" if ok else "dismiss"), clue, noul

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
             "spot": s["id"], "t": round(self.sim.t, 2), "seen": 1, "by": s.get("by", "Clef")}
        self.alerts.append(a)
        self.state = "ALERT"
        self.emit("alert", **a)
        self.state = "INVESTIGATE"
        if self.worker:
            self._think_after(a)

    def _think_after(self, a: dict):
        """qwen38, off the control path: the radio note, then (with map features) where to search next."""
        clue = next(c for c in self.clues if c["name"] == a["clue"])
        closeup = (self.out / a["photo"]).read_bytes()
        crop = (self.out / a["sweep_crop"]).read_bytes() if a.get("sweep_crop") else None
        where = where_words(a["g"])
        lkp = self.spec.get("map", {}).get("lkp")
        if lkp:
            where += f", {math.dist(a['g'], lkp):.0f} m from the trailhead"

        def on_note(n):
            a["note"] = n
            self.emit("note", id=a["id"], **n)
        self.worker.submit(thinker.alert_note, clue, where, a["conf"], a["h"], a["sweep_h"], closeup, crop,
                           on_done=on_note)
        if self.cfg.trail and self.spec.get("map", {}).get("trail") and len(self.queue) > 2:
            rest = [self.sectors[i] for i in self.queue[1:]]

            def on_plan(p):
                self.plans.append(p)
                if "error" in p or not p.get("first"):
                    return self.emit("plan", applied=False, error=p.get("error", "no usable sectors"), **{
                        k: p[k] for k in ("reason", "wall_s") if k in p})
                self.plan_next = p
                self.emit("plan", applied=False, proposed=p["first"], reason=p["reason"], wall_s=p["wall_s"])
            self.worker.submit(thinker.trail_plan, self.cfg.area, self.spec["map"], list(self.alerts), rest,
                               on_done=on_plan)

    # ------------------------------------------------------------ operator
    def _operator(self, cmd: dict):
        """Apply an operator command at a tick. A "_reply" callable in the command (voice) hears the decision, so a
        refused command is not acknowledged aloud as if it had been taken."""
        reply = cmd.pop("_reply", None)
        name = cmd.get("name")
        ok, why = False, "not applicable"
        if name == "return_home":
            if self.state in ("RETURN", "DONE"):
                why = "already returning home" if self.state == "RETURN" else "the flight is over"
            else:
                self._begin_return("operator: return home"); ok, why = True, ""
        elif name == "go_back_to_last_alert":
            if not self.alerts:
                why = "there is no alert yet"
            elif self.state not in ("SWEEP", "RESUME", "INVESTIGATE"):
                why = f"the drone is {self.state.lower()}"
            else:
                a = self.alerts[-1]
                if self.state == "SWEEP":
                    self.resume_xy = (float(self.sim.pos[0]), self.cur["y"])
                self.pending.insert(0, {"g": tuple(a["g"]), "clue": a["clue"], "p_inv": 1.0, "noul": a["conf"],
                                        "frame": None, "crop": a["sweep_crop"], "box": None, "sweep_h": a["sweep_h"],
                                        "t_seen": round(self.sim.t, 2), "revisit": a["id"]})
                if self.state == "INVESTIGATE":     # the spot being checked finishes first; the revisit is next
                    ok, why = True, f"after the spot being checked ({self.spot['id']})"
                else:
                    self._next_spot(); ok, why = True, ""
        self.emit("operator", command=cmd, accepted=ok, reason=why)
        if reply:
            reply(ok, why)

    def status_text(self) -> str:
        found = "; ".join(f"{a['id']} {a['family']} at ({a['g'][0]:.0f}, {a['g'][1]:.0f})" for a in self.alerts)
        return (f"State {self.state}, sector {self.cur['id'] if self.cur else '-'} ({len(self.done_sectors)} of "
                f"{len(self.sectors)} done), area searched "
                f"{100 * self.coverage.fraction():.0f}%, battery {self.battery():.0f}%. Alerts: {found or 'none yet'}.")

    # ------------------------------------------------------------ run
    def run(self, max_ticks: int = 4000, script: dict | None = None, hooks=(), pace: float = 0.0) -> dict:
        """pace > 0: sim time runs at most `pace` x wall-clock time (live console); 0: as fast as it computes."""
        t0 = time.time()
        self.started = True
        self.emit("start", spec=self.spec, clues=self.clues, config=asdict(self.cfg), sweep_h=self.sweep_h,
                  lanes=self.lanes, sectors=self.sectors, home=self.cfg.home)
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
        if self.worker:
            self.emit("state", state=self.state, reason="waiting for qwen38 notes")
            self.worker.drain()
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
        llm = {k: v - self.calls0.get(k, 0) for k, v in thinker.CALLS.items() if v - self.calls0.get(k, 0)}
        return {"llm_calls": sum(llm.values()), "llm_by_role": llm,
                "clef_qwen_idle": stats([d for d in self.decisions if not d["qwen_active"]]),
                "clef_qwen_active": stats([d for d in self.decisions if d["qwen_active"]]),
                "sectors": len(self.sectors), "sectors_done": len(self.done_sectors), "plans": self.plans,
                "state": self.state, "return_reason": self.return_reason, "sim_s": round(self.sim.t, 1),
                "wall_s": round(wall, 1), "flight_s": round(self.flight_s, 1), "battery_used_pct": round(used, 1),
                "state_s": {k: round(v, 1) for k, v in self.state_s.items()},
                "sweep_h": self.sweep_h, "lanes": len(self.lanes), "lane_spacing_m": round(self.lane_spacing, 2),
                "frame_every_m": round(self.frame_every, 2),
                "coverage": round(self.coverage.fraction(), 4), "area_m2_covered": area_m2,
                "frames": self.frames, "candidates": self.n_cands, "clef_sweep": stats(sweep), "clef_confirm": stats(conf),
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
                home=(0.0, -95.0), min_sep: float = 30.0, on_trail: bool = False) -> dict:
    """Place the named items at seeded positions inside the area (inset 12 m, apart, away from home). on_trail: the
    clue items lie along the map's trail in the order a hiker walking from the trailhead would drop them (a path
    seed, for the trail-reasoning test); decoys stay random."""
    rng = random.Random(seed * 977 + 13)
    xs, ys = [p[0] for p in area], [p[1] for p in area]
    size = 2 * (max(max(map(abs, xs)), max(map(abs, ys))) + 20)
    path = []
    if on_trail:
        pts = [p for p in world.map_features(seed, size)["trail"]
               if min(xs) + 10 < p[0] < max(xs) - 10 and min(ys) + 10 < p[1] < max(ys) - 10]
        n_clues = sum(n in clue_names for n in names)
        path = [pts[int(len(pts) * (0.3 + 0.6 * k / max(1, n_clues - 1 or 1)))] for k in range(n_clues)] if pts else []
    placed = []
    for name in names:
        info = item_info(name)
        for _ in range(500):
            if path and name in clue_names:
                px, py = path.pop(0)
                side = rng.choice((-1, 1)) * rng.uniform(2.0, 5.0)
                x, y = px + side * rng.uniform(0.5, 1.0), py + side * rng.uniform(0.2, 0.6)
                break
            x, y = rng.uniform(min(xs) + 12, max(xs) - 12), rng.uniform(min(ys) + 12, max(ys) - 12)
            if all(math.dist((x, y), (q["x"], q["y"])) >= min_sep for q in placed) and math.dist((x, y), home) > 30:
                break
        placed.append({"name": name, "role": "clue" if name in clue_names else "decoy", "prim": info.get("prim"),
                       "obj": info["obj"],
                       "texture": info["texture"], "x": round(x, 2), "y": round(y, 2),
                       "yaw": round(rng.uniform(0, 360), 1), "h": info["extent_m"][2], "size_m": info["size_m"]})
    return world.search_spec(seed, terrain, placed, size=size)


def where_words(g) -> str:
    """A position as a radio team says it. Signed numbers ("-66 m east") made qwen38 write the wrong direction in a
    note (runs/s4-e2e-2/s6: a dog 66 m west and 63 m south was called "66 meters east and 63 meters north")."""
    e, n = g
    return (f"{abs(e):.0f} m {'east' if e >= 0 else 'west'} and {abs(n):.0f} m {'north' if n >= 0 else 'south'} "
            "of the search-area centre")


def _same_item(a: dict, name: str) -> bool:
    """Scoring only: does an alert's clue name the planted item? Catalogue clues use the item's own name; clues
    qwen38 wrote from a description have their own names, so its family words are matched to the catalogue's."""
    if a["clue"] == name:
        return True
    fam = cluelib.CATALOGUE.get(name, {}).get("family", "").lower().replace("gray", "grey")
    said = f"{a.get('family', '')} {a['clue'].replace('_', ' ')}".lower().replace("gray", "grey")
    return bool(fam) and fam in said


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
                     "right_clue": any(_same_item(a, it["name"]) for a in al),
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
    ap.add_argument("--frame-every", type=float, help="along-track frame spacing, m (default: planner.frame_spacing; the fixed 12 m before 14:55 is the A/B control)")
    ap.add_argument("--half", type=float, default=80.0, help="half-width of the square search area, m")
    ap.add_argument("--clef-url", default=clef.URL)
    ap.add_argument("--fault-rate", type=float, default=0.0)
    ap.add_argument("--lockstep", action="store_true", help="pause the world while Clef thinks")
    ap.add_argument("--chase", action="store_true", help="render the chase camera every tick (console, video)")
    ap.add_argument("--pace", type=float, default=0.0, help="sim seconds per wall second (0: as fast as possible)")
    ap.add_argument("--max-ticks", type=int, default=4000)
    ap.add_argument("--think", action="store_true", help="qwen38 on board: notes, trail reasoning, second opinions")
    ap.add_argument("--no-trail", action="store_true", help="with --think: no sector reordering after a find")
    ap.add_argument("--no-second", action="store_true", help="with --think: no second opinion on close calls")
    ap.add_argument("--on-trail", action="store_true", help="place the clue items along the trail (path seeds)")
    ap.add_argument("--describe", help="what the family said, in words: qwen38 writes the clues Clef looks for "
                    "(instead of the catalogue wording); --clues still says which planted items are theirs")
    ap.add_argument("--describe-wav", help="the same description, spoken (Parakeet transcribes it first)")
    ap.add_argument("--speak", action="store_true", help="read alerts, notes and the summary aloud (Kokoro), WAVs saved")
    ap.add_argument("--voice-script", help='JSON {"tick:N" or "alert:K": "fixtures/voice/x.wav"}: spoken commands '
                    "heard, routed by Clef and executed")


def make_mission(a, out: Path, sinks=(), clue_list: list[dict] | None = None) -> SearchMission:
    """The scene and mission for parsed add_args() options (the CLI and the console both use this). clue_list:
    clues written by qwen38 from the family's description (thinker.describe); default, the catalogue's."""
    names = [n for n in a.items.split(",") if n]
    cnames = [n for n in a.clues.split(",") if n]
    h = a.half
    cfg = SearchConfig(area=[(-h, -h), (h, -h), (h, h), (-h, h)], home=(0.0, -h - 15, 2.0), sweep_h=a.sweep_h,
                       frame_every_m=getattr(a, "frame_every", None), thinker=a.think, trail=not a.no_trail,
                       second=not a.no_second)
    spec = build_scene(a.terrain, a.seed, names, cnames, area=cfg.area, home=cfg.home[:2], on_trail=a.on_trail)
    return SearchMission(spec, out, clue_list or cluelib.clues(cnames), cfg, clef_url=a.clef_url, fault_rate=a.fault_rate,
                         seed=a.seed, sinks=sinks, realtime=not a.lockstep, chase=a.chase)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="patrol search")
    add_args(ap)
    a = ap.parse_args(argv)
    out = Path(a.out or ROOT / "runs" / time.strftime("%Y%m%d-%H%M%S-search"))
    out.mkdir(parents=True, exist_ok=True)
    sink = JsonlSink(out / "mission.jsonl")
    worker = speaker = vs = None
    if a.speak or a.voice_script or a.describe_wav:
        from . import voice
        worker = voice.VoiceWorker()
    described = None
    if a.describe or a.describe_wav:
        heard = worker.stt(ROOT / a.describe_wav) if a.describe_wav else {"ok": True, "text": a.describe}
        if not heard.get("ok"):
            raise SystemExit(f"could not transcribe {a.describe_wav}: {heard.get('error')}")
        described = thinker.describe(heard["text"]) | {"stt_ms": heard.get("stt_ms"), "wav": a.describe_wav}
        (out / "describe.json").write_text(json.dumps(described, indent=1))
        print(json.dumps({"heard": heard["text"], "clues": [(c["name"], c["words"]) for c in
                                                             described.get("clues", [])]}), flush=True)
        if not described.get("clues"):
            raise SystemExit(f"qwen38 gave no clues for {heard['text']!r}: {described.get('error')}")
    m = make_mission(a, out, [sink], clue_list=described["clues"] if described else None)
    hooks = []
    if a.speak:
        speaker = voice.Speaker(worker, out, publish=m.emit)
        m.sinks.append(speaker)
    if a.voice_script:
        vs = voice.VoiceScript(json.loads(a.voice_script), worker, speaker, a.clef_url)
        hooks.append(vs)
    try:
        s = m.run(max_ticks=a.max_ticks, pace=a.pace, hooks=hooks)
        if vs:
            vs.join()
        if speaker:
            speaker.drain()
    finally:
        if worker:
            worker.close()
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
