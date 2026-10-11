"""Scene files (patrol/scenes.py): validation, exact placement through search.build_scene and make_mission --scene,
scoring of hand-placed items, and the ground-truth leak test flown over a hand-placed scene."""
from __future__ import annotations

import argparse
import json

import pytest

from patrol import clues, scenes, search, world
from patrol.sim import Sim
from test_search import Poison, fake_clef

EXAMPLE = scenes.DIR / "example.json"


def scene(**kw):
    return {"name": "t", "terrain": "snow", "seed": 1, "half": 40,
            "items": [{"name": "red_jacket", "x": -10, "y": 12, "yaw": 30, "role": "hiker"},
                      {"name": "red_rock", "x": 15, "y": -20, "role": "decoy"}]} | kw


def test_example_scene_loads_by_path_or_name():
    sc = scenes.load(EXAMPLE)
    assert scenes.load("example") == sc == scenes.load("example.json")
    assert sc["terrain"] in world.TERRAINS and sc["half"] == 80.0
    assert scenes.hiker_items(sc) == ["red_jacket", "blue_backpack"]
    assert sc["items"][-1] == {"name": "grey_boulder", "x": 5.0, "y": 0.0, "yaw": 0.0, "role": "decoy"}


def test_available_has_prims_and_built_items():
    names = scenes.available()
    assert set(world.PRIMS) <= set(names) and "blue_backpack" in names


@pytest.mark.parametrize("change, fault", [
    ({"terrain": "lava"}, "terrain"),
    ({"items": [{"name": "unicorn", "x": 0, "y": 0}]}, "not built"),
    ({"items": [{"name": "red_rock", "x": 39, "y": 0}]}, "not inside the area"),
    ({"items": [{"name": "red_rock", "x": 0, "y": 0, "role": "owner"}]}, "role"),
    ({"items": []}, "no items"),
    ({"half": 5}, "half"),
])
def test_bad_scenes_are_refused_with_the_reason(change, fault):
    with pytest.raises(SystemExit, match=fault):
        scenes.validate(scene(**change))


def test_save_round_trips(tmp_path):
    p = scenes.save(scene(), tmp_path / "s.json")
    assert scenes.load(p) == scenes.validate(scene())


def test_build_scene_places_items_exactly():
    sc = scenes.validate(scene())
    area = [(-40, -40), (40, -40), (40, 40), (-40, 40)]
    spec = search.build_scene(sc["terrain"], sc["seed"], [], [], area=area, placements=sc["items"])
    got = [(i["name"], i["x"], i["y"], i["yaw"], i["role"]) for i in spec["items"]]
    assert got == [("red_jacket", -10.0, 12.0, 30.0, "clue"), ("red_rock", 15.0, -20.0, 0.0, "decoy")]
    assert spec["terrain"] == "snow" and spec["seed"] == 1
    for it in spec["items"]:      # clutter stays off hand-placed items too
        assert all(((r["x"] - it["x"]) ** 2 + (r["y"] - it["y"]) ** 2) ** 0.5 > 4 for r in spec["rocks"])


def parsed(*argv):
    ap = argparse.ArgumentParser()
    search.add_args(ap)
    return ap.parse_args(list(argv))


def test_make_mission_with_scene_takes_everything_from_the_file(tmp_path):
    a = parsed("--scene", str(EXAMPLE), "--terrain", "grass", "--seed", "9", "--items", "blue_tarp", "--half", "50")
    m = search.make_mission(a, tmp_path)
    assert (a.terrain, a.seed, a.half) == ("snow", 3, 80.0)
    assert a.items == "red_jacket,blue_backpack,blue_tarp,orange_leaf_pile,grey_boulder"
    assert a.clues == "red_jacket,blue_backpack"
    assert [c["name"] for c in m.clues] == ["red_jacket", "blue_backpack"]
    assert m.cfg.area[2] == (80.0, 80.0)
    assert not set(search.TRUTH_KEYS) & set(m.spec)


def test_scene_hiker_items_without_catalogue_wording_need_a_description(tmp_path):
    p = scenes.save(scene(items=[{"name": "blue_tarp", "x": 0, "y": 0, "role": "hiker"}]), tmp_path / "s.json")
    with pytest.raises(SystemExit, match="describe"):
        search.make_mission(parsed("--scene", str(p)), tmp_path)
    described = [{"name": "tarp", "family": "tarp", "words": "a blue plastic tarp", "size_m": 2.0}]
    m = search.make_mission(parsed("--scene", str(p)), tmp_path, clue_list=described)
    assert m.clues == described


def test_score_counts_the_hikers_items_of_a_scene(tmp_path):
    sc = scenes.validate(scene())
    spec = search.build_scene(sc["terrain"], sc["seed"], [], [], placements=sc["items"])
    (tmp_path / "scene.json").write_text(json.dumps(spec))
    alerts = [{"type": "alert", "id": 1, "g": [-9.0, 11.5], "clue": "red_jacket", "t": 50.0},
              {"type": "alert", "id": 2, "g": [15.5, -20.0], "clue": "red_jacket", "t": 80.0}]
    (tmp_path / "mission.jsonl").write_text("".join(json.dumps(e) + "\n" for e in alerts))
    sc = search.score(tmp_path)
    assert sc["recall"] == "1/1" and sc["false_alerts"] == [2]


def test_hand_placed_scene_flies_without_reading_ground_truth(tmp_path, monkeypatch):
    """The leak test of test_search over a hand-placed scene with a real item mesh in it."""
    sc = scenes.validate(scene(half=30, items=[{"name": "red_jacket", "x": -8, "y": 10, "yaw": 30, "role": "hiker"},
                                               {"name": "grey_boulder", "x": 12, "y": -15, "role": "decoy"}]))
    h = sc["half"]
    cfg = search.SearchConfig(area=[(-h, -h), (h, -h), (h, h), (-h, h)], home=(0.0, -h - 10, 2.0), sweep_h=40.0,
                              W=320, H=240, frame_every_m=12.0)
    spec = search.build_scene(sc["terrain"], sc["seed"], [], [], area=cfg.area, home=cfg.home[:2],
                              placements=sc["items"])
    events = []
    m = search.SearchMission(spec, tmp_path, clues.clues(scenes.hiker_items(sc)), cfg, sinks=[events.append],
                             realtime=False, save_frames=False, ask=fake_clef(["dismiss", "confirm"]))
    for k in search.TRUTH_KEYS:
        spec[k] = Poison()
    assert not set(search.TRUTH_KEYS) & set(m.spec) and m.sim.spec is m.spec
    for meth in ("project", "visible_defects", "vegetation_clearance"):
        monkeypatch.setattr(Sim, meth, lambda *a, **k: (_ for _ in ()).throw(AssertionError("truth via Sim")))
    s = m.run(max_ticks=3000)
    assert s["state"] == "DONE" and s["return_reason"] == "area covered"
    assert {"investigate", "confirm", "alert"} <= {e["type"] for e in events}
