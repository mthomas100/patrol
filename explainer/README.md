# Patrol explainer

A one-page, brochure-style explanation of Patrol for people who have not read the code: what it is, how the models
fit together, what the drone does, the evidence so far and the known faults. Open `index.html` in a browser (it
works from a local file; fonts fall back to system faces offline).

## Files

| path | what |
|---|---|
| `index.html` | the page: hand-written prose and structure, with generated parts between markers |
| `figures.py` | every diagram and chart as static SVG; chart numbers live in its `DATA` block with their sources |
| `build.py` | injects the figures and the hero flight map's data into `index.html` |
| `data/flight.json` | the flight drawn on the hero map (a copy of what is injected) |
| `assets/` | curated, compressed stills and a 3 MB cut of `demo/fallback.mp4` |

## Updating it

1. Change prose directly in `index.html`. Every claim names its evidence (a run, a report or a code path) in a
   `.src` line; keep that habit, and never quote a number you have not read from a file.
2. Change a chart's numbers in `figures.py` `DATA`, or a diagram's function, then rebuild.
3. To draw a different flight on the hero map: `python3 explainer/build.py runs/<run>` (any search run with
   `mission.jsonl`, `scene.json`, `score.json`). With no argument it uses `runs/s5-live-owner`.
4. Rebuild: `python3 explainer/build.py` from `projects/patrol`. Standard library only, no model calls.
5. Update the stamp in the contents rail and the footer, keep `assets/` to a few MB, and commit with
   `git commit -- projects/patrol/explainer`.

Facts that the project's memory files had wrong or stale when this was written (code wins): the search has no radio
sink; the terrain is a flat plane; the second opinion makes the drone hover; voice acknowledgements wait for the
mission's decision since 15a0ed5; 70 offline tests.
