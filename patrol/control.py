"""The confidence gate, the deterministic fallback policy and the state machine. Pure logic: no MuJoCo, no HTTP.

The decision model advises; this code commands. It decides which actions are legal in each state, turns Clef's
probabilities into an action with cost weights, replaces failed, late or unsure decisions with a deterministic
policy (shown as FALLBACK), and owns altitude, standoff, speed, battery, geofence and return-home (shown as SAFETY).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

ACTIONS = ("continue", "hover_and_photograph", "go_back", "flag_damage")

# Cost weights on Clef's probabilities: missing a defect costs far more than a hover (one or two seconds) does.
# Measured on fixtures/m0-seed0 (runs/m0/SUMMARY.md): cruise-frame hover probability 0.24-0.35 near a defect vs
# continue around 0.5-0.6; confirm-photo flag probability 0.44 on damage vs 0.04 on intact equipment.
CRUISE_WEIGHTS = {"continue": 1.0, "hover_and_photograph": 1.8, "go_back": 1.0, "flag_damage": 2.0}
CONFIRM_WEIGHTS = {"continue": 1.0, "flag_damage": 3.0}       # flag when p(flag) > 0.25

# Confirm-photo component questions that also justify a flag (Clef's own nouls, thresholded by code). Measured on
# runs/m2-probe (seed 0, 24-degree zoom): clean photos reach vegetation 0.58 (perspective: a background tree looks
# close to a wire) and at most 0.06 on the others; defects aimed within 2 m reach 0.43-0.84 on their own noul.
NOUL_FLAG = {"insulator_damaged": 0.35, "conductor_frayed": 0.35, "foreign_object": 0.35, "vegetation_close": 0.65}

GATE = {
    "deadline_ms": 2500.0,    # a cruise answer later than this is dropped (the drone has moved on)
    "hover_deadline_ms": 8000.0,   # hovering is the safe state, so a confirm answer may take longer
    "min_top_prob": 0.30,     # Clef torn between options: its top raw probability below this
    "min_sure": 0.60,         # Clef's own "how sure" score (0..2) below this
    "stale_m": 4.0,           # a cruise answer is stale once the drone has flown this far since its frame
    "hard_deadline_ms": 10000.0,
}

# Cruise rule: "look closer" evidence is hover + flag (a flag needs a photo first anyway). Hover when
# LOOK_GAIN * (p_hover + p_flag) beats p_continue. Chosen on runs/m2-seed0's logged frames: 1.3 gives every planted
# defect at least one trigger frame while 2 of 90 clean frames hover (a hover costs seconds, not a false flag).
LOOK_GAIN = 1.3


@dataclass
class Gated:
    action: str
    source: str               # "clef" | "fallback" | "safety" | "operator"
    reason: str = ""
    legal: tuple = ACTIONS
    weighted: dict = field(default_factory=dict)

    @property
    def label(self) -> str:
        return {"clef": "CLEF", "fallback": "FALLBACK", "safety": "SAFETY", "operator": "OPERATOR"}[self.source]


def gate(dec, legal: tuple, weights: dict, fallback_action: str, fallback_why: str,
         deadline_ms: float | None = None, moved_m: float | None = None) -> Gated:
    """Turn a clef.Decision into an action. Any failure, stale answer or low confidence -> FALLBACK.
    Staleness: by distance flown while waiting when moved_m is given, else by deadline_ms."""
    if not dec.ok:
        return Gated(fallback_action, "fallback", f"decision failed ({dec.error[:60]}); {fallback_why}", legal)
    if moved_m is not None and (moved_m > GATE["stale_m"] or dec.latency_ms > GATE["hard_deadline_ms"]):
        return Gated(fallback_action, "fallback", f"stale (flew {moved_m:.1f} m in {dec.latency_ms:.0f} ms); "
                     f"{fallback_why}", legal)
    if moved_m is None and dec.latency_ms > (deadline_ms or GATE["deadline_ms"]):
        return Gated(fallback_action, "fallback", f"late ({dec.latency_ms:.0f} ms); {fallback_why}", legal)
    probs = {a: dec.probs.get(a, 0.0) for a in legal}
    top = max(probs.values()) if probs else 0.0
    if top < GATE["min_top_prob"] or dec.sure < GATE["min_sure"]:
        return Gated(fallback_action, "fallback",
                     f"low confidence (top {top:.2f}, sure {dec.sure:.2f}); {fallback_why}", legal)
    w = {a: round(p * weights.get(a, 1.0), 4) for a, p in probs.items()}
    if weights is CRUISE_WEIGHTS:
        w = {"continue": round(probs["continue"], 4),
             "hover_and_photograph": round(LOOK_GAIN * (probs["hover_and_photograph"] + probs["flag_damage"]), 4),
             "go_back": round(probs["go_back"], 4)}
    return Gated(max(w, key=w.get), "clef", "", legal, w)


def confirm_gate(dec, fallback_why: str) -> Gated:
    """Gate for the hover photo: the weighted flag/continue choice, upgraded to a flag when one of Clef's component
    answers clears its threshold."""
    g = gate(dec, ("continue", "flag_damage"), CONFIRM_WEIGHTS, "continue", fallback_why,
             deadline_ms=GATE["hover_deadline_ms"])
    if g.source == "clef" and g.action == "continue":
        over = {k: v for k, v in dec.nouls.items() if v >= NOUL_FLAG.get(k, 2.0)}
        if over:
            k = max(over, key=over.get)
            g.action, g.reason = "flag_damage", f"{k} = {over[k]:.2f} >= {NOUL_FLAG[k]}"
    return g


# ---------------------------------------------------------------- mission state
@dataclass
class Target:
    """A point the gimbal was aimed at, which a hover photographs."""
    x: float
    y: float
    z: float
    why: str = ""

    def near(self, other: "Target", r: float = 8.0) -> bool:
        return abs(self.x - other.x) < r and abs(self.y - other.y) < 2.0


@dataclass
class Flag:
    id: str
    target: Target
    photo: str
    t: float
    probs: dict
    nouls: dict
    defect_guess: str
    source: str
    note: dict | None = None          # filled by escalation (M2)
    clearance: float | None = None    # rangefinder: nearest tree to a conductor, m (None: no trees in view)


@dataclass
class Config:
    length: float = 300.0
    standoff_y: float = -12.0
    altitude: float = 13.0
    transit_altitude: float = 18.0
    cruise: float = 3.0
    revisit_speed: float = 2.0
    transit: float = 5.5
    home: tuple = (-15.0, -12.0, 13.0)
    dt: float = 0.5
    battery_start: float = 100.0
    drain_per_s: float = 0.12        # percent per second flying
    drain_hover_per_s: float = 0.15
    reserve: float = 6.0             # percent kept on top of what the trip home costs
    hover_hold_ticks: int = 2        # ticks held still while photographing
    max_revisits: int = 2
    blind_m: float = 1.6             # most distance the drone may fly per decision; sets the speed governor
    min_cruise: float = 0.8


class StateMachine:
    """States: CRUISE -> HOVER -> CRUISE ...; REVISIT -> HOVER; RETURN -> DONE. One tick per control period."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.state = "CRUISE"
        self.battery = cfg.battery_start
        self.target: Target | None = None
        self.hover_ticks = 0
        self.photographed: list[Target] = []     # spots settled by a confident confirmation
        self.unconfirmed: list[Target] = []      # photographed, but the confirm was a FALLBACK
        self.suspect: tuple[float, Target] | None = None     # (score, target) seen in cruise, not yet photographed
        self.revisits = 0
        self.flags: list[Flag] = []
        self.return_reason = ""
        self.phase = "near"
        self.corridor_done = False

    # ------------------------------------------------------------ helpers
    def photographed_near(self, t: Target) -> bool:
        """Settled spots, or spots already photographed twice without a confident answer."""
        return any(t.near(p) for p in self.photographed) or sum(t.near(p) for p in self.unconfirmed) >= 2

    def tried_near(self, t: Target) -> bool:
        return self.photographed_near(t) or any(t.near(p) for p in self.unconfirmed)

    def return_cost(self, pos) -> float:
        d = math.dist(pos, self.cfg.home)
        return d / self.cfg.transit * self.cfg.drain_per_s

    def governed_cruise(self, latency_ema_s: float) -> float:
        """The drone slows when its decisions slow: at most blind_m metres flown per decision."""
        if latency_ema_s <= 0:
            return self.cfg.cruise
        return max(self.cfg.min_cruise, min(self.cfg.cruise, self.cfg.blind_m / latency_ema_s))

    def velocity_hold(self, pos, vx: float, z: float | None = None):
        """Velocity command: vx along the corridor, P control holding the standoff line and altitude."""
        z = self.cfg.altitude if z is None else z
        return (vx, 0.8 * (self.cfg.standoff_y - pos[1]), 0.8 * (z - pos[2]))

    # ------------------------------------------------------------ safety, every tick, before any decision
    def safety(self, pos, speed: float) -> Gated | None:
        if self.state in ("RETURN", "DONE"):
            return None
        if self.battery <= self.return_cost(pos) + self.cfg.reserve:
            return self.begin_return("battery reserve reached")
        if pos[0] > self.cfg.length + 8:
            self.corridor_done = True
            return self.begin_return("corridor complete")
        if abs(pos[1] - self.cfg.standoff_y) > 4 or abs(pos[2] - self.cfg.altitude) > 4:
            return self.begin_return("left the standoff corridor")
        return None

    def begin_return(self, why: str) -> Gated:
        self.state, self.return_reason = "RETURN", why
        return Gated("continue", "safety", f"return home: {why}", ())

    def drain(self, dt: float):
        self.battery -= dt * (self.cfg.drain_hover_per_s if self.state == "HOVER" else self.cfg.drain_per_s)

    # ------------------------------------------------------------ fallback policy (deterministic)
    def fallback_cruise(self, x: float, look: Target, tower_ahead: bool) -> tuple[str, str]:
        """Standard protocol without the model: photograph every tower's insulators once, otherwise keep going."""
        if tower_ahead and not self.tried_near(look):
            return "hover_and_photograph", "protocol: photograph each tower once"
        return "continue", "protocol: keep flying"

    # ------------------------------------------------------------ the decision hook for CRUISE frames
    def on_cruise(self, g: Gated, look: Target, dec) -> Gated:
        """Apply a gated cruise decision. Refuse illegal or pointless actions with a reason."""
        anomaly = (dec.probs.get("hover_and_photograph", 0) + dec.probs.get("flag_damage", 0)) if dec.ok else 0
        if not self.photographed_near(look) and (self.suspect is None or anomaly > self.suspect[0]):
            if anomaly >= 0.30:
                self.suspect = (anomaly, look)
        if g.action in ("hover_and_photograph", "flag_damage"):
            if self.photographed_near(look):
                g.reason = (g.reason + "; " if g.reason else "") + "refused: already photographed here"
                g.action = "continue"
            else:
                self.state, self.target, self.hover_ticks = "HOVER", look, 0
        elif g.action == "go_back":
            if self.suspect and self.revisits < self.cfg.max_revisits and not self.photographed_near(self.suspect[1]):
                self.state, self.target = "REVISIT", self.suspect[1]
                self.revisits += 1
            else:
                g.reason = (g.reason + "; " if g.reason else "") + "refused: nothing unphotographed behind"
                g.action = "continue"
        return g

    def on_confirm(self, g: Gated):
        """After the hover photo: flag or move on. A confident answer settles the spot; a FALLBACK leaves it open
        for one more look if Clef later asks for it."""
        (self.photographed if g.source == "clef" else self.unconfirmed).append(self.target)
        if self.suspect and self.suspect[1].near(self.target):
            self.suspect = None
        self.state = "CRUISE"

    # ------------------------------------------------------------ operator commands (voice routing lands here)
    def operator(self, cmd: dict) -> Gated | None:
        name = cmd.get("name")
        if name == "return_home" and self.state not in ("RETURN", "DONE"):
            self.begin_return("operator asked")
            return Gated("continue", "operator", "return home (operator)", ())
        if name == "revisit_last_flag" and self.flags and self.state not in ("RETURN", "DONE"):
            f = self.flags[-1]
            self.photographed = [p for p in self.photographed if not p.near(f.target)]
            self.state, self.target = "REVISIT", f.target
            return Gated("go_back", "operator", f"revisit flag {f.id} (operator)", ())
        if name == "change_target" and cmd.get("phase") in ("near", "middle", "far"):
            self.phase = cmd["phase"]
            return Gated("continue", "operator", f"inspect the {self.phase} phase (operator)", ())
        return None
