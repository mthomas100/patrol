# Patrol run report: faults

**Result: PASS**

- [x] corridor completed
- [x] returned home
- [x] recall >= 0.0
- [x] false alarms <= 99
- [x] every flag has a photo

## What ran

Scene `corridor` seed 1, 300 m, 6 planted defects. Versions: {"python": "3.12.14", "mujoco": "3.15.0", "clef": "clef-flash-mlx (mlx-community/clef-flash-8bit @ dfa0993, upstream Cloudflare/clef-flash @ 17f0b0a)", "llm": "qwen38 via llama-swap :8090", "git": "f4ddd15"}.

Headline: recall 0.833, false alarms 1, LLM on 0.0% of decisions, decision latency median 414.3 ms (p90 421.1), Clef decided 71% of decisions, LLM note names the planted defect type for 0/5 found defects, wall time 53.5 s.

| measure | value |
|---|---|
| ticks | 319 |
| sim_time_s | 207.9 |
| wall_time_s | 53.5 |
| realtime_factor | 3.89 |
| distance_m | 662.7 |
| battery_end | 80.4 |
| return_reason | corridor complete |
| decisions | 160 |
| decisions_ok | 116 |
| decision_sources | {"FALLBACK": 46, "CLEF": 114, "RANGEFINDER": 1, "SAFETY": 1} |
| latency_ms | {"median": 414.3, "p90": 421.1, "max": 562.8} |
| photos | 11 |
| llm_calls | 0 |
| llm_frame_fraction | 0.0 |
| notes_ok | 0 |
| recall | 0.833 |
| false_alarms | ["F6"] |

## Planted defects against flags

| defect | type | x | found by | photo triggered by | Clef's guess | LLM note |
|---|---|---|---|---|---|---|
| D1 | vegetation | 20 | F1 (CLEF) | RANGEFINDER | vegetation_close |  |
| D2 | broken_insulator | 100 | F2 (CLEF) | CLEF | foreign_object |  |
| D3 | frayed_conductor | 130 | F3 (CLEF) | CLEF | foreign_object |  |
| D4 | foreign_object | 200 | F4 (CLEF) | CLEF | foreign_object |  |
| D5 | foreign_object | 229 | MISSED |  |  |  |
| D6 | broken_insulator | 250 | F5 (CLEF) | FALLBACK | foreign_object |  |

False alarms: F6 at x=263 (note: none)

## Photos

| photo | target x | triggered by | decided by | action | p(flag) | clearance m |
|---|---|---|---|---|---|---|
| media/photos/photo_01_x000.0.jpg | 0 | FALLBACK | CLEF | continue | 0.07 | None |
| media/photos/photo_02a_x016.3.jpg | 19 | RANGEFINDER | CLEF | flag_damage | 0.59 | 0.17 |
| media/photos/photo_03_x050.0.jpg | 50 | FALLBACK | CLEF | continue | 0.07 | None |
| media/photos/photo_04_x100.0.jpg | 100 | CLEF | CLEF | flag_damage | 0.72 | None |
| media/photos/photo_05a_x123.5.jpg | 127 | CLEF | CLEF | flag_damage | 0.57 | 12.12 |
| media/photos/photo_06_x150.0.jpg | 150 | FALLBACK | CLEF | continue | 0.18 | None |
| media/photos/photo_07_x200.0.jpg | 200 | CLEF | CLEF | flag_damage | 0.77 | None |
| media/photos/photo_08a_x226.2.jpg | 229 | CLEF | CLEF | continue | 0.10 | None |
| media/photos/photo_09_x250.0.jpg | 250 | FALLBACK | CLEF | flag_damage | 0.38 | None |
| media/photos/photo_10a_x259.6.jpg | 263 | CLEF | CLEF | flag_damage | 0.47 | None |
| media/photos/photo_11_x300.0.jpg | 300 | FALLBACK | CLEF | continue | 0.08 | None |

Mission log: `faults/mission.jsonl`; frames and photos under `faults/media/` (not in git).
