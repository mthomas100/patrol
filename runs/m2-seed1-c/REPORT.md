# Patrol run report: m2-seed1-c

**Result: PASS**

- [x] corridor completed
- [x] returned home
- [x] recall >= 0.5
- [x] false alarms <= 0
- [x] every flag has a photo
- [x] every flag has an LLM note

## What ran

Scene `corridor` seed 1, 300 m, 6 planted defects. Versions: {"python": "3.12.14", "mujoco": "3.15.0", "clef": "clef-flash-mlx (mlx-community/clef-flash-8bit @ dfa0993, upstream Cloudflare/clef-flash @ 17f0b0a)", "llm": "qwen38 via llama-swap :8090", "git": "0c23486"}.

| measure | value |
|---|---|
| ticks | 275 |
| sim_time_s | 505.3 |
| wall_time_s | 480.1 |
| realtime_factor | 1.05 |
| distance_m | 664.6 |
| battery_end | 83.3 |
| return_reason | corridor complete |
| decisions | 131 |
| decisions_ok | 119 |
| decision_sources | {"CLEF": 114, "FALLBACK": 17, "SAFETY": 1} |
| latency_ms | {"median": 1943.0, "p90": 4456.2, "max": 5743.9} |
| photos | 7 |
| llm_calls | 3 |
| llm_frame_fraction | 0.0229 |
| notes_ok | 3 |
| recall | 0.5 |
| false_alarms | [] |

## Planted defects against flags

| defect | type | x | found by | Clef's guess | LLM note |
|---|---|---|---|---|---|
| D1 | vegetation | 20 | MISSED |  |  |
| D2 | broken_insulator | 100 | F1 (CLEF) | foreign_object | foreign_object, medium: A dark, elongated object is attached to the middle section of the right-hand insulator string, and several small dark fragments are visible falling below the cr |
| D3 | frayed_conductor | 130 | MISSED |  |  |
| D4 | foreign_object | 200 | F2 (CLEF) | foreign_object | foreign_object, medium: A brown, spiky object resembling a large nest or animal is resting on the top surface of the crossarm, directly above the insulator string. |
| D5 | foreign_object | 229 | MISSED |  |  |
| D6 | broken_insulator | 250 | F3 (CLEF) | conductor_frayed | foreign_object, medium: A dark, elongated object is attached diagonally across the middle of the suspended insulator string, and several small dark fragments are visible falling below  |

## Photos

| photo | target x | decided by | action | p(flag) |
|---|---|---|---|---|
| media/photos/photo_01_x050.0.jpg | 50 | CLEF | continue | 0.07 |
| media/photos/photo_02_x100.0.jpg | 100 | CLEF | flag_damage | 0.63 |
| media/photos/photo_03_x150.0.jpg | 150 | FALLBACK | continue | 0.00 |
| media/photos/photo_04_x200.0.jpg | 200 | CLEF | flag_damage | 0.48 |
| media/photos/photo_05_x250.0.jpg | 250 | CLEF | flag_damage | 0.69 |
| media/photos/photo_06a_x258.1.jpg | 261 | CLEF | continue | 0.07 |
| media/photos/photo_07_x300.0.jpg | 300 | CLEF | continue | 0.06 |

Mission log: `m2-seed1-c/mission.jsonl`; frames and photos under `m2-seed1-c/media/` (not in git).
