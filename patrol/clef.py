"""Clef-Flash client: one frame plus symbolic telemetry in, four-action decision out, via POST /v1/systemone.

Every option is described in words (bare labels route badly in testing). The questions are decided jointly in one
forward pass. Errors and timeouts never raise into the control loop; they return Decision(ok=False) and the gate
turns that into FALLBACK.
"""
from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

URL = "http://127.0.0.1:8097/v1/systemone"
MODEL = "clef-flash-mlx"

ACTIONS = {
    "continue": "the towers, insulators, conductors and trees in view all look intact and normal, or no line "
                "equipment is close enough to judge; keep flying along the corridor",
    "hover_and_photograph": "something on a tower, insulator string, conductor or a nearby tree looks unusual "
                            "(a gap, a dark spot, an odd shape, a branch near a wire) but is too small or unclear "
                            "to judge from here; stop and take a zoomed close-up photo",
    "go_back": "a possible problem was just passed and is now at the edge of the picture or out of view; fly back "
               "a short way to look at it again",
    "flag_damage": "damage or a hazard is clearly visible: insulator discs missing, cracked or hanging askew; "
                   "conductor strands broken and splayed out; a tree crown touching or within a metre of a "
                   "conductor; a bird nest or debris lodged on a crossarm or conductor",
}

DEFECTS = {
    "none": "no defect visible; the equipment looks normal",
    "broken_insulator": "an insulator string (the stack of glass discs hanging from the crossarm) has missing, "
                        "cracked, scorched or tilted discs",
    "frayed_conductor": "a conductor (the long hanging wire) has broken strands sticking out or a burnt patch",
    "vegetation": "a tree crown reaches up into the wires or is within a metre of a conductor",
    "foreign_object": "a bird nest, sticks, plastic sheet, kite or other debris is on a crossarm or hanging on a wire",
}

SURE = ["not sure at all: the picture is unclear or the equipment is too far away",
        "fairly sure",
        "certain: the equipment is close and clearly visible"]


def schema(defect_types=True) -> dict:
    q = {
        "action": {"type": "choice", "instructions": "Pick the drone's next action for this camera frame.",
                   "criteria": ACTIONS},
        "damage": {"type": "noul", "instructions": "Is any damage or hazard visible on the power line equipment in "
                   "the picture: a broken insulator, a frayed conductor, a tree touching a wire, or a nest or "
                   "debris on the line?"},
        "sure": {"type": "score", "instructions": "How sure are you about what the picture shows?", "criteria": SURE},
    }
    if defect_types:
        q["defect"] = {"type": "choice", "instructions": "Which kind of defect, if any, is visible?",
                       "criteria": DEFECTS}
    return q


COMPONENT_NOULS = {
    "insulator_damaged": "Is any glass insulator string (the stack of discs hanging under the crossarm) missing "
                         "discs, with a gap in the stack, or with a disc tilted, cracked or blackened?",
    "conductor_frayed": "Does any conductor wire have broken strands sticking out or a blackened burnt patch?",
    "vegetation_close": "Is a tree crown touching a wire or within a metre of one?",
    "foreign_object": "Is a bird nest, sticks, a plastic sheet, a kite or other debris on a crossarm or a wire?",
}


def confirm_schema() -> dict:
    """Asked of the zoomed hover photo. Only flag_damage and continue are legal here (code owns legality)."""
    return {
        "action": {"type": "choice", "instructions": "This is a zoomed close-up of the nearest line equipment. "
                   "Decide whether to flag damage or continue the patrol.",
                   "criteria": {"flag_damage": ACTIONS["flag_damage"],
                                "continue": "the equipment in the close-up looks intact and normal; resume the "
                                            "patrol"}},
        **{k: {"type": "noul", "instructions": v} for k, v in COMPONENT_NOULS.items()},
        "sure": {"type": "score", "instructions": "How sure are you about what the close-up shows?",
                 "criteria": SURE},
    }


def state_text(tel: dict, context: dict | None = None) -> str:
    """Symbolic state beside the image: what code knows that pixels do not show."""
    c = context or {}
    lines = [
        "You are the visual inspector on a power-line inspection drone. The attached picture is the drone's "
        + ("zoomed close-up photo" if c.get("camera") == "zoom" else
           "two zoomed close-up photos (just behind and just ahead of the aim point)" if c.get("camera") == "zoom2"
           else "forward-left inspection camera frame")
        + ". The drone flies alongside a high-voltage line; the camera looks at the towers, the glass insulator "
          "strings hanging from each crossarm, the three conductors and the trees nearby.",
        f"Position along the corridor: {tel['x']:.0f} m of {c.get('length', 300):.0f} m; altitude {tel['z']:.0f} m; "
        f"speed {tel['speed']:.1f} m/s.",
    ]
    if c.get("hovering"):
        lines.append("The drone is hovering and has just taken close-up photos of the spot that looked unusual.")
    if "clearance" in c:
        if c["clearance"] is None:
            lines.append("Rangefinder (lidar): no trees in view of the close-up.")
        else:
            lines.append(f"Rangefinder (lidar): the nearest tree surface is {c['clearance']:.1f} m from the nearest "
                         "conductor; a tree is only a hazard within about 1 m, and a tree that merely appears behind "
                         "or in front of a wire in the photo is not touching it.")
    if c.get("revisit"):
        lines.append("The drone flew back to re-inspect a spot that looked suspicious.")
    if c.get("flags_here"):
        lines.append(f"Damage already flagged within 10 m of here: {c['flags_here']}.")
    return "\n".join(lines)


@dataclass
class Decision:
    ok: bool
    action: str = "continue"
    probs: dict = field(default_factory=dict)
    confidence: float = 0.0
    damage: float = 0.0
    sure: float = 0.0           # expected level 0..2
    defect: str = "none"
    defect_probs: dict = field(default_factory=dict)
    nouls: dict = field(default_factory=dict)
    extra: dict = field(default_factory=dict)     # other choice answers, e.g. "where"
    latency_ms: float = 0.0
    input_tokens: int = 0
    error: str = ""

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


def ask(jpeg, state: str, questions: dict | None = None, timeout: float = 10.0, url: str = URL) -> Decision:
    """jpeg: bytes, or a list of bytes for several images decided together."""
    imgs = jpeg if isinstance(jpeg, (list, tuple)) else [jpeg]
    req = {"model": MODEL, "state": state, "questions": questions or schema(),
           "images": ["data:image/jpeg;base64," + base64.b64encode(j).decode() for j in imgs]}
    t0 = time.perf_counter()
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, json.dumps(req).encode(),
                                                          {"Content-Type": "application/json"}), timeout=timeout)
        body = json.loads(r.read())
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        return Decision(ok=False, error=f"{type(e).__name__}: {e}"[:200],
                        latency_ms=round((time.perf_counter() - t0) * 1000, 1))
    ms = round((time.perf_counter() - t0) * 1000, 1)
    a = body.get("answers") or {}
    if "action" not in a:
        return Decision(ok=False, error=f"no action in answer: {str(body)[:160]}", latency_ms=ms)
    act = a["action"]
    d = Decision(ok=True, action=act["choice"], probs=act.get("probabilities", {}),
                 confidence=float(act.get("confidence", 0.0)), latency_ms=ms,
                 input_tokens=int((body.get("usage") or {}).get("input_tokens", 0)))
    d.nouls = {k: float(v["noul"]) for k, v in a.items() if v.get("type") == "noul"}
    d.extra = {k: v["choice"] for k, v in a.items() if v.get("type") == "choice" and k not in ("action", "defect")}
    if "damage" in a:
        d.damage = float(a["damage"]["noul"])
    elif d.nouls:
        d.damage = max(d.nouls.values())
    if "sure" in a:
        d.sure = float(a["sure"]["score"])
    if "defect" in a:
        d.defect = a["defect"]["choice"]
        d.defect_probs = a["defect"].get("probabilities", {})
    return d


def health(url: str = "http://127.0.0.1:8097/health", timeout: float = 3.0) -> bool:
    try:
        return json.loads(urllib.request.urlopen(url, timeout=timeout).read()).get("status") == "ok"
    except Exception:
        return False
