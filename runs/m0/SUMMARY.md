# M0 evidence (patrol-1, 2026-10-11)

Simulator: MuJoCo 3.15.0 (pip, CGL offscreen), scene from `patrol/world.py`, seed 0, one broken insulator (D1, tower 2,
near phase). Fixture frames: `fixtures/m0-seed0/` (20 inspect-camera frames along a pass + 5 zoom photos, with
ground truth in `frames.jsonl`). Made with `bin/patrol frames fixtures/m0-seed0`.

Latency, Clef-Flash MLX 8-bit on :8097 (shared with conjure-1), `bin/patrol bench fixtures/m0-seed0 --sizes ...`:

| frame width | input tokens | median ms | p90 ms | source |
|---|---|---|---|---|
| 256 | 932 | 563 | 593 | bench.jsonl (first pass, fixed wide camera) |
| 384 | 970 | 414 | 607 | bench.jsonl |
| 512 | 1054 | 446 | 449 | bench.jsonl |
| 768 | 1294 | 582 | 588 | bench.jsonl |
| 512 | 1054 | 433 | 819 | bench2.jsonl (inspect camera) |

Image size barely moves cost (about 360 extra tokens from 256 to 768 px); the text schema dominates. 512 px chosen.

Detection findings:
- Fixed wide camera (62 degrees): the defect is a few pixels; Clef saw nothing (damage at most 0.13). Not usable.
- Code-aimed inspect camera (34 degrees, aimed from the corridor map): weak but real signal: damage up to 0.44 on
  defect frames vs at most 0.18 on clean ones; hover probability 0.24-0.35 vs at most 0.23 (tune1.txt).
- Zoom photo (16 degrees) of the broken insulator: damage 0.65-0.78 vs 0.01-0.02 on intact insulators; with a
  confirm-only schema (flag_damage vs continue) flag 0.44 vs 0.04 on all four intact ones.
- Clef reads the broken insulator partly as "foreign object" (dark askew disc, shards).
- A healthy background tree reads as "vegetation within a metre" (0.59-0.69) through perspective.
