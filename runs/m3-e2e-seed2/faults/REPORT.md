# Patrol run report: faults

**Result: PASS**

- [x] corridor completed
- [x] returned home
- [x] recall >= 0.0
- [x] false alarms <= 99
- [x] every flag has a photo

## What ran

Scene `corridor` seed 2, 300 m, 6 planted defects. Versions: {"python": "3.12.14", "mujoco": "3.15.0", "clef": "clef-flash-mlx (mlx-community/clef-flash-8bit @ dfa0993, upstream Cloudflare/clef-flash @ 17f0b0a)", "llm": "qwen38 via llama-swap :8090", "git": "f4ddd15"}.

Headline: recall 0.833, false alarms 0, LLM on 0.0% of decisions, decision latency median 424.8 ms (p90 518.2), Clef decided 71% of decisions, LLM note names the planted defect type for 0/5 found defects, wall time 54.5 s.

| measure | value |
|---|---|
| ticks | 308 |
| sim_time_s | 203.7 |
| wall_time_s | 54.5 |
| realtime_factor | 3.74 |
| distance_m | 660.4 |
| battery_end | 81.1 |
| return_reason | corridor complete |
| decisions | 152 |
| decisions_ok | 109 |
| decision_sources | {"CLEF": 108, "FALLBACK": 43, "RANGEFINDER": 2, "SAFETY": 1} |
| latency_ms | {"median": 424.8, "p90": 518.2, "max": 1800.4} |
| photos | 10 |
| llm_calls | 0 |
| llm_frame_fraction | 0.0 |
| notes_ok | 0 |
| recall | 0.833 |
| false_alarms | [] |

## Planted defects against flags

| defect | type | x | found by | photo triggered by | Clef's guess | LLM note |
|---|---|---|---|---|---|---|
| D1 | vegetation | 32 | F1 (RANGEFINDER) | RANGEFINDER | vegetation_close |  |
| D2 | broken_insulator | 100 | F2 (CLEF) | FALLBACK | foreign_object |  |
| D3 | frayed_conductor | 132 | F3 (CLEF) | CLEF | foreign_object |  |
| D4 | foreign_object | 200 | F4 (CLEF) | CLEF | foreign_object |  |
| D5 | foreign_object | 218 | MISSED |  |  |  |
| D6 | broken_insulator | 250 | F5 (CLEF) | FALLBACK | foreign_object |  |

## Photos

| photo | target x | triggered by | decided by | action | p(flag) | clearance m |
|---|---|---|---|---|---|---|
| media/photos/photo_01_x000.0.jpg | 0 | FALLBACK | FALLBACK | continue | 0.00 | None |
| media/photos/photo_02a_x026.9.jpg | 30 | RANGEFINDER | RANGEFINDER | flag_damage | 0.00 | 0.06 |
| media/photos/photo_03_x050.0.jpg | 50 | FALLBACK | CLEF | continue | 0.14 | None |
| media/photos/photo_04_x100.0.jpg | 100 | FALLBACK | CLEF | flag_damage | 0.26 | None |
| media/photos/photo_05a_x119.5.jpg | 122 | CLEF | FALLBACK | continue | 0.00 | None |
| media/photos/photo_06a_x122.2.jpg | 125 | CLEF | FALLBACK | continue | 0.00 | None |
| media/photos/photo_07a_x127.7.jpg | 131 | CLEF | CLEF | flag_damage | 0.49 | None |
| media/photos/photo_08_x200.0.jpg | 200 | CLEF | CLEF | flag_damage | 0.66 | None |
| media/photos/photo_09_x250.0.jpg | 250 | FALLBACK | CLEF | flag_damage | 0.76 | None |
| media/photos/photo_10_x300.0.jpg | 300 | FALLBACK | FALLBACK | continue | 0.00 | None |

Mission log: `faults/mission.jsonl`; frames and photos under `faults/media/` (not in git).
