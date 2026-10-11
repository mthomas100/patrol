# Patrol run report: faults

**Result: PASS**

- [x] corridor completed
- [x] returned home
- [x] recall >= 0.0
- [x] false alarms <= 99
- [x] every flag has a photo

## What ran

Scene `corridor` seed 1, 300 m, 6 planted defects. Versions: {"python": "3.12.14", "mujoco": "3.15.0", "clef": "clef-flash-mlx (mlx-community/clef-flash-8bit @ dfa0993, upstream Cloudflare/clef-flash @ 17f0b0a)", "llm": "qwen38 via llama-swap :8090", "git": "a9ec8eb"}.

Headline: recall 0.5, false alarms 0, LLM on 0.0% of decisions, decision latency median 411.3 ms (p90 423.7), Clef decided 72% of decisions, LLM note names the planted defect type for 0/3 found defects, wall time 54.1 s.

| measure | value |
|---|---|
| ticks | 317 |
| sim_time_s | 207.9 |
| wall_time_s | 54.1 |
| realtime_factor | 3.84 |
| distance_m | 661.2 |
| battery_end | 80.5 |
| return_reason | corridor complete |
| decisions | 159 |
| decisions_ok | 115 |
| decision_sources | {"FALLBACK": 45, "CLEF": 114, "RANGEFINDER": 1, "SAFETY": 1} |
| latency_ms | {"median": 411.3, "p90": 423.7, "max": 2580.2} |
| photos | 11 |
| llm_calls | 0 |
| llm_frame_fraction | 0.0 |
| notes_ok | 0 |
| recall | 0.5 |
| false_alarms | [] |

## Planted defects against flags

| defect | type | x | found by | photo triggered by | Clef's guess | LLM note |
|---|---|---|---|---|---|---|
| D1 | vegetation | 20 | F1 (CLEF) | RANGEFINDER | vegetation_close |  |
| D2 | broken_insulator | 100 | F2 (CLEF) | CLEF | foreign_object |  |
| D3 | frayed_conductor | 130 | F3 (CLEF) | CLEF | foreign_object |  |
| D4 | foreign_object | 200 | MISSED |  |  |  |
| D5 | foreign_object | 229 | MISSED |  |  |  |
| D6 | broken_insulator | 250 | MISSED |  |  |  |

## Photos

| photo | target x | triggered by | decided by | action | p(flag) | clearance m |
|---|---|---|---|---|---|---|
| media/photos/photo_01_x000.0.jpg | 0 | FALLBACK | CLEF | continue | 0.07 | None |
| media/photos/photo_02a_x016.2.jpg | 19 | RANGEFINDER | CLEF | flag_damage | 0.60 | 0.16 |
| media/photos/photo_03_x050.0.jpg | 50 | FALLBACK | CLEF | continue | 0.07 | None |
| media/photos/photo_04_x100.0.jpg | 100 | CLEF | CLEF | flag_damage | 0.26 | None |
| media/photos/photo_05a_x123.1.jpg | 126 | CLEF | CLEF | flag_damage | 0.53 | 12.11 |
| media/photos/photo_06_x150.0.jpg | 150 | FALLBACK | CLEF | continue | 0.17 | None |
| media/photos/photo_07_x200.0.jpg | 200 | CLEF | FALLBACK | continue | 0.00 | None |
| media/photos/photo_08_x200.0.jpg | 200 | CLEF | CLEF | continue | 0.15 | None |
| media/photos/photo_09_x250.0.jpg | 250 | CLEF | FALLBACK | continue | 0.00 | None |
| media/photos/photo_10_x250.0.jpg | 250 | CLEF | FALLBACK | continue | 0.00 | None |
| media/photos/photo_11_x300.0.jpg | 300 | FALLBACK | CLEF | continue | 0.07 | None |

Mission log: `faults/mission.jsonl`; frames and photos under `faults/media/` (not in git).
