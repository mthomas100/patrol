# Patrol: an offline search drone that looks for one missing person's things

A family says "he had a blue backpack, an orange tent and a grey dog". The operator tells the drone. It sweeps the
search area, and a fast local decision model (Clef-Flash) checks odd-looking spots against those words. On a "maybe"
the drone flies down for a closer look, then confirms or dismisses it. A confirmed find becomes an alert with
coordinates and a photo, and the sweep resumes. Everything runs on one Mac with no internet. The drone and terrain
are simulated in MuJoCo.

It is decision support: a person reviews every alert. The simulator proves the behaviour, not real-world detection.

## Try it

**Using a coding agent?** Point it at [`SETUP.md`](SETUP.md): "Set up Patrol on this Mac by following SETUP.md." It
checks your Mac, asks before every large download, wires up the models and proves the result with a test flight.

**By hand:** follow the same file. In short:

1. An Apple Silicon Mac with 32 GB of memory or more.
2. Clef-Flash (10.7 GB) served through the public `local-decision` repo on port 8097.
3. The eight 3D search items: a mesh bundle, or a rebuild with the public `local-3d` (m3d) repo.
4. `tests/e2e_search.sh --only 1,2,3,4 --no-think`, then the live console in your browser.
5. Optional: any local vision chat model on port 8090 (clue wording and alert notes), and `local-voice` for speech.

**No suitable Mac?** [`HOSTED.md`](HOSTED.md) sketches running it with hosted models instead: Clef-Flash on Cloudflare
Workers AI and any vision chat model through a proxy. It is untested and no longer offline.

## What is in this folder

| Path | What |
|---|---|
| `patrol/` | the code: planner, anomaly finder, Clef client, gate, mission, console |
| `bin/patrol` | the command line (`search`, `console`, `fly`) |
| `tests/` | unit tests (`pytest`) and the end-to-end scenarios (`e2e_search.sh`) |
| `demo/` | the recorded fallback flight |
| `explainer/` | a page explaining the project with results |
| `BRIEF.md`, `STATUS.md`, `DECISIONS.md`, `LOG.md`, `HANDOFF.md` | how it was built: the plan, measured results with evidence, choices and reasons, the build log |

## Results so far

With a simulated 20-minute battery, 17 of 18 scenario flights passed over three seed sets, with 0 false alerts. The
one miss was a clue in ground the drone never reached before the battery ran out. The first run on held-out items
(never used for tuning) found 24 of 25. The battery is now 30 minutes and those runs are being repeated. Details and
evidence: `STATUS.md`.
