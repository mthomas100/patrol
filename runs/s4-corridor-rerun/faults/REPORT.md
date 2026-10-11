# Patrol run report: faults

**Result: PASS**

- [x] corridor completed
- [x] returned home
- [x] recall >= 0.0
- [x] false alarms <= 99
- [x] every flag has a photo

## What ran

Scene `corridor` seed 1, 300 m, 6 planted defects. Versions: {"python": "3.12.14", "mujoco": "3.15.0", "clef": "clef-flash-mlx (mlx-community/clef-flash-8bit @ dfa0993, upstream Cloudflare/clef-flash @ 17f0b0a)", "llm": "qwen38 via llama-swap :8090", "git": "a9ec8eb"}.

Headline: recall 0.667, false alarms 0, LLM on 0.0% of decisions, decision latency median 413.4 ms (p90 418.6), Clef decided 72% of decisions, LLM note names the planted defect type for 0/4 found defects, wall time 54.7 s.

| measure | value |
|---|---|
| ticks | 320 |
| sim_time_s | 209.9 |
| wall_time_s | 54.7 |
| realtime_factor | 3.84 |
| distance_m | 664.9 |
| battery_end | 80.3 |
| return_reason | corridor complete |
| decisions | 160 |
| decisions_ok | 116 |
| decision_sources | {"FALLBACK": 45, "CLEF": 115, "RANGEFINDER": 1, "SAFETY": 1} |
| latency_ms | {"median": 413.4, "p90": 418.6, "max": 2581.5} |
| photos | 11 |
| llm_calls | 0 |
| llm_frame_fraction | 0.0 |
| notes_ok | 0 |
| recall | 0.667 |
| false_alarms | [] |

## Planted defects against flags

| defect | type | x | found by | photo triggered by | Clef's guess | LLM note |
|---|---|---|---|---|---|---|
| D1 | vegetation | 20 | F1 (CLEF) | RANGEFINDER | vegetation_close |  |
| D2 | broken_insulator | 100 | F2 (CLEF) | CLEF | insulator_damaged |  |
| D3 | frayed_conductor | 130 | F3 (CLEF) | CLEF | conductor_frayed |  |
| D4 | foreign_object | 200 | F4 (CLEF) | CLEF | foreign_object |  |
| D5 | foreign_object | 229 | MISSED |  |  |  |
| D6 | broken_insulator | 250 | MISSED |  |  |  |

## Photos

| photo | target x | triggered by | decided by | action | p(flag) | clearance m |
|---|---|---|---|---|---|---|
| media/photos/photo_01_x000.0.jpg | 0 | FALLBACK | CLEF | continue | 0.07 | None |
| media/photos/photo_02a_x016.3.jpg | 19 | RANGEFINDER | CLEF | flag_damage | 0.55 | 0.16 |
| media/photos/photo_03_x050.0.jpg | 50 | FALLBACK | CLEF | continue | 0.07 | None |
| media/photos/photo_04_x100.0.jpg | 100 | CLEF | CLEF | flag_damage | 0.77 | None |
| media/photos/photo_05a_x126.3.jpg | 129 | CLEF | CLEF | flag_damage | 0.82 | 12.29 |
| media/photos/photo_06_x150.0.jpg | 150 | FALLBACK | CLEF | continue | 0.18 | None |
| media/photos/photo_07_x200.0.jpg | 200 | CLEF | CLEF | flag_damage | 0.74 | None |
| media/photos/photo_08a_x226.0.jpg | 229 | CLEF | CLEF | continue | 0.12 | None |
| media/photos/photo_09_x250.0.jpg | 250 | CLEF | FALLBACK | continue | 0.00 | None |
| media/photos/photo_10_x250.0.jpg | 250 | CLEF | FALLBACK | continue | 0.00 | None |
| media/photos/photo_11_x300.0.jpg | 300 | FALLBACK | CLEF | continue | 0.09 | None |

Mission log: `faults/mission.jsonl`; frames and photos under `faults/media/` (not in git).
