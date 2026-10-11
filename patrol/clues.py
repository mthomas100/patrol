"""Clues: what the family said, what it looks like from above, and the Clef questions built from them.

A clue is {"name", "family", "words", "size_m"}: the family's words ("blue backpack"), the from-above description
Clef is asked about, and a rough real size that sets the sweep height (planner.sweep_height). CATALOGUE holds
hand-written descriptions for every item built for the simulator; they stand in for qwen38's wording until S3
(`describe`, which turns a free-text description into clues). The blue backpack's words are the ones S0 measured.

Clef judges one picture per call (it cannot say where in a frame something is: runs/m2-probe), so the sweep asks
about one finder crop at a time, and the confirm asks about the zoom close-up of one spot.
"""
from __future__ import annotations

SURE = ["not sure at all: the picture is unclear or the object is too far away or too small",
        "fairly sure",
        "certain: the object is close and clearly visible"]

CATALOGUE = {   # tuning: blue_backpack, orange_tent, red_jacket; held out: grey_dog, green_sleeping_bag, yellow_helmet, sos_rocks
    "blue_backpack": {"family": "blue backpack", "size_m": 0.55,
                      "words": "a blue hiking backpack lying on the ground: a bag with shoulder straps and pockets, "
                               "about half a metre long"},
    "orange_tent": {"family": "orange tent", "size_m": 2.2,
                    "words": "an orange camping tent: a dome of orange fabric about two metres across, pitched on "
                             "the ground"},
    "red_jacket": {"family": "red jacket", "size_m": 0.8,
                   "words": "a red jacket lying on the ground: a piece of clothing with a hood and two sleeves, "
                            "under a metre long"},
    "grey_dog": {"family": "grey dog", "size_m": 1.0,
                 "words": "a grey dog lying on the ground: an animal with four legs, a head and a tail, about a "
                          "metre long"},
    "green_sleeping_bag": {"family": "green sleeping bag", "size_m": 2.0,
                           "words": "a green sleeping bag lying flat on the ground: a long padded bag about two "
                                    "metres long, rounded at one end"},
    "yellow_helmet": {"family": "yellow helmet", "size_m": 0.3,
                      "words": "a yellow climbing helmet on the ground: a small round hard hat about thirty "
                               "centimetres across"},
    "sos_rocks": {"family": "SOS made of rocks", "size_m": 5.0,
                  "words": "the letters SOS laid out on the ground with small stones, a few metres long"},
}
# generic confusers in open terrain, the same for every clue (not chosen from the held-out decoys)
OTHER = ("something else of a similar colour that is not one of the missing person's belongings: a flat tarp or "
         "plastic sheet, a rock, a log, a bush or a patch of leaves, or a shadow")
NOTHING = "no object at all, only snow or grass, rocks, trees or plants"
STATE = ("You are the visual spotter on a search-and-rescue drone looking for a missing hiker's belongings in open "
         "terrain. Altitude {h:.0f} m above ground; camera {cam}.")


def clues(names: list[str]) -> list[dict]:
    return [{"name": n, **CATALOGUE[n]} for n in names]


def sweep_schema(cl: list[dict]) -> dict:
    """One finder crop at sweep height: worth a closer look? One noul per clue (S0 wording)."""
    some = "; or ".join(c["words"] for c in cl)
    q = {"action": {"type": "choice", "instructions": "Search-and-rescue drone camera frame. Is anything in the "
                    "picture worth flying closer to check against the missing person's belongings?",
                    "criteria": {"continue": "nothing in the picture could be one of the missing person's "
                                             "belongings; only snow or grass, rocks, trees and shadows",
                                 "investigate": f"something in the picture could be {some}; fly closer to check"}}}
    for c in cl:
        q[c["name"]] = {"type": "noul", "instructions": f"Is {c['words']} visible anywhere in the picture?"}
    q["sure"] = {"type": "score", "instructions": "How sure are you about what the picture shows?", "criteria": SURE}
    return q


def confirm_schema(cl: list[dict]) -> dict:
    """The zoom close-up of one spot: which clue, if any. CONFIRM needs both the choice and that clue's own noul
    (the corridor's false flags had the choice right but every noul under 0.14)."""
    crit = {c["name"]: c["words"] for c in cl}
    crit.update(other=OTHER, nothing=NOTHING)
    q = {"action": {"type": "choice", "instructions": "Close-up photo from a search drone. What is the object?",
                    "criteria": crit}}
    for c in cl:
        q[c["name"]] = {"type": "noul", "instructions": f"Is the object in the photo {c['words']}, and not a tarp, "
                        "a sheet or another object?"}
    q["sure"] = {"type": "score", "instructions": "How sure are you about what the close-up shows?",
                 "criteria": SURE}
    return q


def sweep_state(h: float) -> str:
    return STATE.format(h=h, cam="crop around an odd spot found by the anomaly finder")


def confirm_state(h: float) -> str:
    return STATE.format(h=h, cam="zoom, aimed at the spot") + " The drone has flown over an odd spot and taken " \
        "this close-up."
