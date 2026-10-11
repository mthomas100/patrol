"""Offline tests of the sweep planner: footprint, lanes, sweep height and the coverage grid (pure Python)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from patrol import planner  # noqa: E402

SQUARE = [(-80, -80), (80, -80), (80, 80), (-80, 80)]
TRIANGLE = [(-80, -80), (80, -80), (0, 80)]          # 160 m wide at the south edge, a point at the north


def frames(lns, h=40.0):
    """Ground rectangle swept by nadir frames flying each lane: its x range plus half a frame at each end."""
    along, cross = planner.footprint(h)
    for ln in lns:
        x0, x1 = sorted((ln["x0"], ln["x1"]))
        yield [(x0 - along / 2, ln["y"] - cross / 2), (x1 + along / 2, ln["y"] - cross / 2),
               (x1 + along / 2, ln["y"] + cross / 2), (x0 - along / 2, ln["y"] + cross / 2)]


# ------------------------------------------------------------------ footprint, spacing, height
def test_footprint_and_spacing_at_40_m():
    along, cross = planner.footprint(40.0)
    assert (along, cross) == pytest.approx((24.5, 32.6), abs=0.1)
    assert cross == pytest.approx(along * 4 / 3)
    assert planner.lane_spacing(40.0) == pytest.approx(26.1, abs=0.05)
    assert planner.lane_spacing(40.0, overlap=0.0) == pytest.approx(cross)
    assert planner.footprint(20.0) == pytest.approx((along / 2, cross / 2))      # scales with height
    assert planner.footprint(40.0, vfov_deg=62.0)[0] > along                     # and with the field of view


def test_sweep_height_follows_the_smallest_clue_and_clips():
    assert planner.sweep_height([0.55, 2.2]) == 40.0
    assert planner.sweep_height([0.3]) == pytest.approx(21.8, abs=0.05)
    assert planner.sweep_height([0.1]) == 20.0
    assert planner.sweep_height([]) == 40.0
    assert planner.sweep_height([3.0]) == 40.0                                   # never above hi
    assert planner.sweep_height([0.3, 0.9]) == planner.sweep_height([0.3])        # only the smallest matters
    assert planner.sweep_height([0.3], lo=25.0) == 25.0


# ------------------------------------------------------------------ lanes
def test_lanes_over_a_square_alternate_and_span_the_area():
    ls = planner.lanes(SQUARE, 26.1)
    assert len(ls) == 7 and [ln["i"] for ln in ls] == list(range(7))
    step = 160 / 7                                                               # 7 even bands, each under 26.1 m
    assert ls[0]["y"] == pytest.approx(-80 + step / 2) and ls[-1]["y"] == pytest.approx(80 - step / 2)
    assert [b["y"] - a["y"] for a, b in zip(ls, ls[1:])] == pytest.approx([step] * 6)
    for k, ln in enumerate(ls):
        want = (-80.0, 80.0) if k % 2 == 0 else (80.0, -80.0)                    # lane 0 flies toward +x, then back
        assert (ln["x0"], ln["x1"]) == pytest.approx(want)
    assert planner.lanes_length(ls) == pytest.approx(7 * 160)
    assert all(type(ln[k]) is float for ln in ls for k in ("y", "x0", "x1"))
    json.dumps(ls)


def test_lanes_do_not_depend_on_the_winding_of_the_area():
    a, b = planner.lanes(SQUARE, 26.1), planner.lanes(SQUARE[::-1], 26.1)
    assert [v for ln in a for v in ln.values()] == pytest.approx([v for ln in b for v in ln.values()])


def test_triangle_lanes_shrink_toward_the_apex():
    ls = planner.lanes(TRIANGLE, 26.1)
    widths = [abs(ln["x1"] - ln["x0"]) for ln in ls]
    assert len(ls) >= 3 and widths == sorted(widths, reverse=True) and widths[0] > 5 * widths[-1]
    for ln in ls:                          # for this triangle the width at height y is 80 - y, centred on x = 0
        assert abs(ln["x1"] - ln["x0"]) == pytest.approx(80 - ln["y"])
        assert (ln["x0"] + ln["x1"]) / 2 == pytest.approx(0.0, abs=1e-9)
    assert ls[0]["x0"] < ls[0]["x1"] and ls[1]["x0"] > ls[1]["x1"]              # still alternating
    assert planner.lanes_length(ls) == pytest.approx(sum(80 - ln["y"] for ln in ls))


def test_an_area_narrower_than_the_spacing_gets_one_centred_lane():
    ls = planner.lanes([(0, 0), (100, 0), (100, 10), (0, 10)], 26.1)
    assert len(ls) == 1 and ls[0]["y"] == pytest.approx(5.0)
    assert (ls[0]["x0"], ls[0]["x1"]) == pytest.approx((0.0, 100.0))


def test_lanes_are_spread_evenly_and_reach_both_edges():
    def depth(d):
        return planner.lanes([(0, 0), (100, 0), (100, d), (0, d)], 26.1)
    assert [ln["y"] for ln in depth(70.0)] == pytest.approx([70 / 6, 35.0, 70 - 70 / 6])   # 3 bands of 23.3 m
    assert len(depth(52.2)) == 2 and len(depth(52.3)) == 3                       # a third band once two fall short
    assert len(depth(26.0)) == 1 and depth(26.0)[0]["y"] == pytest.approx(13.0)


def test_a_bad_spacing_is_refused():
    with pytest.raises(ValueError):
        planner.lanes(SQUARE, 0.0)


# ------------------------------------------------------------------ coverage
def test_coverage_whole_half_and_twice():
    cov = planner.Coverage(SQUARE)
    assert cov.fraction() == 0.0
    half = [(-80, -80), (0, -80), (0, 80), (-80, 80)]
    assert cov.mark(half) == 40 * 80                                             # 2 m cells: 40 columns of 80
    assert cov.fraction() == pytest.approx(0.5, abs=0.01)
    assert cov.mark(half) == 0                                                   # marking twice adds nothing
    assert cov.mark(SQUARE) == 40 * 80 and cov.fraction() == 1.0                 # only the other half is new
    assert cov.mark(SQUARE) == 0 and cov.mark(None) == 0


def test_coverage_accepts_either_winding_for_the_area_and_the_marked_polygon():
    half = [(-80, -80), (0, -80), (0, 80), (-80, 80)]
    for area in (SQUARE, SQUARE[::-1]):
        for poly in (half, half[::-1]):
            cov = planner.Coverage(area)
            assert cov.mark(poly) == 40 * 80 and cov.fraction() == pytest.approx(0.5, abs=0.01)
    assert planner.Coverage(TRIANGLE[::-1]).grid() == planner.Coverage(TRIANGLE).grid()


def test_coverage_counts_only_cells_inside_the_area():
    cov = planner.Coverage(TRIANGLE)
    n = cov.mark([(-500, -500), (500, -500), (500, 500), (-500, 500)])          # far bigger than the area
    assert cov.fraction() == 1.0 and n == pytest.approx(3200, rel=0.02)         # 12800 m2 of 4 m2 cells
    rows = cov.grid()["rows"]
    assert sum(r.count("1") for r in rows) == n and not any("0" in r for r in rows)
    assert rows[0] == "1" * 80 and rows[-1] == "." * 80                          # wide south row, empty apex row
    assert planner.Coverage(TRIANGLE).mark([(-1, -1), (1, -1)]) == 0             # fewer than three points


def test_coverage_grid_is_compact_and_southern_row_first():
    cov = planner.Coverage(SQUARE, cell=2.0)
    cov.mark([(-80, -80), (80, -80), (80, -70), (-80, -70)])                     # a strip along the south edge
    g = cov.grid()
    assert (g["x0"], g["y0"], g["cell"], g["nx"], g["ny"]) == (-80.0, -80.0, 2.0, 80, 80)
    assert len(g["rows"]) == 80 and all(len(r) == 80 for r in g["rows"])
    assert g["rows"][0] == "1" * 80 and g["rows"][4] == "1" * 80 and g["rows"][5] == "0" * 80
    assert cov.fraction() == pytest.approx(5 / 80)
    assert json.loads(json.dumps(g)) == g


def test_a_coarser_cell_and_an_awkward_area_size():
    area = [(0, 0), (101, 0), (101, 51), (0, 51)]                                # 101 x 51 m in 5 m cells: 21 x 11
    cov = planner.Coverage(area, cell=5.0)
    assert cov.mark(area) == 20 * 10 and cov.fraction() == 1.0                  # last column and row: centre outside
    g = cov.grid()
    assert (g["nx"], g["ny"]) == (21, 11)
    assert g["rows"][0] == "1" * 20 + "." and g["rows"][-1] == "." * 21
    with pytest.raises(ValueError):
        planner.Coverage(SQUARE, cell=0.0)


def test_planned_lanes_with_their_frames_cover_the_square():
    cov = planner.Coverage(SQUARE)
    lns = planner.lanes(SQUARE, planner.lane_spacing(40.0))
    assert len(lns) == 7
    seen = []
    for poly in frames(lns):
        cov.mark(poly)
        seen.append(cov.fraction())
    assert seen == sorted(seen) and seen[0] < 0.25                               # each lane adds ground
    assert cov.fraction() == 1.0


def test_dropping_a_lane_leaves_a_gap_the_coverage_shows():
    lns = planner.lanes(SQUARE, planner.lane_spacing(40.0))
    cov = planner.Coverage(SQUARE)
    for poly in frames(lns[:2] + lns[3:]):
        cov.mark(poly)
    assert 0.7 < cov.fraction() < 1.0


# ------------------------------------------------------------------ frame spacing, lane overlap, sector order (14:55)
def shots(lns, step, h):
    """One nadir footprint every `step` metres along each lane (both ends included)."""
    along, cross = planner.footprint(h)
    for ln in lns:
        x0, x1 = sorted((ln["x0"], ln["x1"]))
        n = max(1, int((x1 - x0) // step))
        for k in range(n + 1):
            x = x0 + k * step
            yield [(x - along / 2, ln["y"] - cross / 2), (x + along / 2, ln["y"] - cross / 2),
                   (x + along / 2, ln["y"] + cross / 2), (x - along / 2, ln["y"] + cross / 2)]


def test_frame_spacing_is_the_old_12_m_at_40_m_and_scales_below():
    assert planner.frame_spacing(40.0) == pytest.approx(12.0, abs=0.05)
    assert planner.frame_spacing(21.82) == pytest.approx(0.49 * planner.footprint(21.82)[0])
    along = planner.footprint(20.0)[0]
    assert planner.frame_spacing(20.0, clue_m=9.0) <= along - 9.0 + 1e-9    # a long clue still fits whole in a frame
    assert planner.frame_spacing(20.0, clue_m=50.0) == pytest.approx(along / 4)   # never collapses to nothing


def test_fixed_12_m_frames_leave_gaps_at_21_8_m_and_the_scaled_ones_do_not():
    h = 21.82
    lns = planner.lanes(SQUARE, planner.lane_spacing(h))
    old, new = planner.Coverage(SQUARE), planner.Coverage(SQUARE)
    for poly in shots(lns, 14.6, h):          # the p90 spacing measured on runs/s4-e2e-2/s5 with the fixed 12 m
        old.mark(poly)
    for poly in shots(lns, planner.frame_spacing(h) + 3.0, h):   # plus a whole tick of travel at 6 m/s
        new.mark(poly)
    assert old.fraction() < 0.95 and new.fraction() == 1.0


def test_lane_overlap_holds_the_largest_clue_and_is_unchanged_for_small_ones():
    assert planner.lane_spacing(40.0, min_overlap_m=2.64) == planner.lane_spacing(40.0)
    assert planner.lane_spacing(21.82, min_overlap_m=2.64) == planner.lane_spacing(21.82)
    cross = planner.footprint(21.82)[1]
    assert planner.lane_spacing(21.82, min_overlap_m=6.0) == pytest.approx(cross - 6.0)
    assert planner.lane_spacing(21.82, min_overlap_m=99.0) == pytest.approx(cross / 4)
    lns = planner.lanes(SQUARE, planner.lane_spacing(21.82, min_overlap_m=6.0))
    gaps = [b["y"] - a["y"] for a, b in zip(lns, lns[1:])]
    assert len(lns) == 14 and max(gaps) <= cross - 6.0 + 1e-9


def test_nearest_first_order_and_route_length():
    secs = planner.sectors(planner.lanes(SQUARE, planner.lane_spacing(40.0)), 40.0)
    order = planner.nearest_first(secs, (0.0, -95.0))
    assert sorted(order) == list(range(len(secs)))
    stale = [s for s in secs if s["lane"] != 3] + [s for s in secs if s["lane"] == 3]   # a band left for last
    m_stale, _ = planner.route_m(stale, (0.0, 0.0))
    m_nn, end = planner.route_m([stale[i] for i in planner.nearest_first(stale, (0.0, 0.0))], (0.0, 0.0))
    assert m_nn < m_stale
    one = secs[0]
    m, end = planner.route_m([one], (one["x1"] + 5.0, one["y"]))       # flown from the nearer end
    assert m == pytest.approx(5.0 + abs(one["x1"] - one["x0"])) and end == (one["x0"], one["y"])
