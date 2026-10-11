# Patrol run report: faults

**Result: PASS**

- [x] corridor completed
- [x] returned home
- [x] recall >= 0.0
- [x] false alarms <= 99
- [x] every flag has a photo

## What ran

Scene `corridor` seed 0, 300 m, 6 planted defects. Versions: {"python": "3.12.14", "mujoco": "3.15.0", "clef": "clef-flash-mlx (mlx-community/clef-flash-8bit @ dfa0993, upstream Cloudflare/clef-flash @ 17f0b0a)", "llm": "qwen38 via llama-swap :8090", "git": "f4ddd15"}.

Headline: recall 1.0, false alarms 0, LLM on 0.0% of decisions, decision latency median 412.15 ms (p90 416.5), Clef decided 67% of decisions, LLM note names the planted defect type for 0/6 found defects, wall time 51.2 s.

| measure | value |
|---|---|
| ticks | 323 |
| sim_time_s | 207.7 |
| wall_time_s | 51.2 |
| realtime_factor | 4.06 |
| distance_m | 660.5 |
| battery_end | 80.1 |
| return_reason | corridor complete |
| decisions | 165 |
| decisions_ok | 112 |
| decision_sources | {"CLEF": 110, "FALLBACK": 55, "RANGEFINDER": 1, "SAFETY": 1} |
| latency_ms | {"median": 412.15, "p90": 416.5, "max": 674.6} |
| photos | 12 |
| llm_calls | 0 |
| llm_frame_fraction | 0.0 |
| notes_ok | 0 |
| recall | 1.0 |
| false_alarms | [] |

## Planted defects against flags

| defect | type | x | found by | photo triggered by | Clef's guess | LLM note |
|---|---|---|---|---|---|---|
| D1 | vegetation | 30 | F1 (CLEF) | RANGEFINDER | vegetation_close |  |
| D2 | broken_insulator | 100 | F2 (CLEF) | CLEF | foreign_object |  |
| D3 | frayed_conductor | 129 | F3 (CLEF) | CLEF | foreign_object |  |
| D4 | foreign_object | 200 | F4 (CLEF) | CLEF | foreign_object |  |
| D5 | foreign_object | 224 | F5 (CLEF) | CLEF | foreign_object |  |
| D6 | broken_insulator | 250 | F6 (CLEF) | CLEF | insulator_damaged |  |

## Photos

| photo | target x | triggered by | decided by | action | p(flag) | clearance m |
|---|---|---|---|---|---|---|
| media/photos/photo_01_x000.0.jpg | 0 | FALLBACK | CLEF | continue | 0.06 | None |
| media/photos/photo_02a_x025.9.jpg | 29 | RANGEFINDER | CLEF | flag_damage | 0.72 | 0.07 |
| media/photos/photo_03_x100.0.jpg | 100 | CLEF | CLEF | flag_damage | 0.76 | None |
| media/photos/photo_04a_x121.2.jpg | 124 | CLEF | FALLBACK | continue | 0.00 | None |
| media/photos/photo_05a_x124.0.jpg | 127 | CLEF | CLEF | flag_damage | 0.39 | None |
| media/photos/photo_06_x150.0.jpg | 150 | FALLBACK | CLEF | continue | 0.07 | None |
| media/photos/photo_07a_x164.6.jpg | 168 | CLEF | FALLBACK | continue | 0.00 | None |
| media/photos/photo_08_x200.0.jpg | 200 | CLEF | CLEF | flag_damage | 0.53 | None |
| media/photos/photo_09a_x214.5.jpg | 217 | CLEF | CLEF | flag_damage | 0.29 | None |
| media/photos/photo_10_x250.0.jpg | 250 | CLEF | FALLBACK | continue | 0.00 | None |
| media/photos/photo_11_x250.0.jpg | 250 | CLEF | CLEF | flag_damage | 0.75 | None |
| media/photos/photo_12_x300.0.jpg | 300 | FALLBACK | CLEF | continue | 0.07 | None |

Mission log: `faults/mission.jsonl`; frames and photos under `faults/media/` (not in git).
