# Patrol run report: m2-seed0-c

**Result: PASS**

- [x] corridor completed
- [x] returned home
- [x] recall >= 0.5
- [x] false alarms <= 0
- [x] every flag has a photo
- [x] every flag has an LLM note

## What ran

Scene `corridor` seed 0, 300 m, 6 planted defects. Versions: {"python": "3.12.14", "mujoco": "3.15.0", "clef": "clef-flash-mlx (mlx-community/clef-flash-8bit @ dfa0993, upstream Cloudflare/clef-flash @ 17f0b0a)", "llm": "qwen38 via llama-swap :8090", "git": "0c23486"}.

| measure | value |
|---|---|
| ticks | 291 |
| sim_time_s | 537.1 |
| wall_time_s | 432.4 |
| realtime_factor | 1.24 |
| distance_m | 660.4 |
| battery_end | 82.2 |
| return_reason | corridor complete |
| decisions | 143 |
| decisions_ok | 106 |
| decision_sources | {"CLEF": 101, "FALLBACK": 42, "SAFETY": 1} |
| latency_ms | {"median": 3031.8, "p90": 4571.8, "max": 5793.0} |
| photos | 11 |
| llm_calls | 4 |
| llm_frame_fraction | 0.028 |
| notes_ok | 4 |
| recall | 0.667 |
| false_alarms | [] |

## Planted defects against flags

| defect | type | x | found by | Clef's guess | LLM note |
|---|---|---|---|---|---|
| D1 | vegetation | 30 | F1 (CLEF) | vegetation_close | vegetation, critical: The lidar rangefinder confirms a tree canopy is only 0.1 m from the nearest conductor, which is well within the 1 m safety threshold. The visual obstruction in  |
| D2 | broken_insulator | 100 | F2 (CLEF) | foreign_object | foreign_object, medium: A dark, elongated object is wedged horizontally across the middle section of the insulator string, and several smaller dark fragments are visible on the ground  |
| D3 | frayed_conductor | 129 | MISSED |  |  |
| D4 | foreign_object | 200 | F3 (CLEF) | foreign_object | foreign_object, medium: A large brown object, resembling a bird's nest, is resting on top of the crossarm near the insulator attachment point. |
| D5 | foreign_object | 224 | MISSED |  |  |
| D6 | broken_insulator | 250 | F4 (CLEF) | conductor_frayed | foreign_object, medium: A dark, irregular object is attached to the middle section of the right-hand insulator string, and a second similar object is visible floating just below the co |

## Photos

| photo | target x | decided by | action | p(flag) |
|---|---|---|---|---|
| media/photos/photo_01a_x024.2.jpg | 27 | CLEF | flag_damage | 0.77 |
| media/photos/photo_02_x050.0.jpg | 50 | CLEF | continue | 0.05 |
| media/photos/photo_03_x100.0.jpg | 100 | CLEF | flag_damage | 0.48 |
| media/photos/photo_04_x150.0.jpg | 150 | FALLBACK | continue | 0.00 |
| media/photos/photo_05a_x160.0.jpg | 163 | CLEF | continue | 0.09 |
| media/photos/photo_06a_x169.5.jpg | 172 | CLEF | continue | 0.07 |
| media/photos/photo_07_x200.0.jpg | 200 | CLEF | flag_damage | 0.58 |
| media/photos/photo_08a_x216.3.jpg | 219 | CLEF | continue | 0.06 |
| media/photos/photo_09_x250.0.jpg | 250 | FALLBACK | continue | 0.00 |
| media/photos/photo_10_x250.0.jpg | 250 | CLEF | flag_damage | 0.58 |
| media/photos/photo_11_x300.0.jpg | 300 | FALLBACK | continue | 0.00 |

Mission log: `m2-seed0-c/mission.jsonl`; frames and photos under `m2-seed0-c/media/` (not in git).
