# Patrol run report: m1-clef-seed0-b

**Result: PASS**

- [x] corridor completed
- [x] returned home
- [x] recall >= 1.0
- [x] false alarms <= 0
- [x] every flag has a photo

## What ran

Scene `corridor` seed 0, 300 m, 1 planted defects. Versions: {"python": "3.12.14", "mujoco": "3.15.0", "clef": "clef-flash-mlx (mlx-community/clef-flash-8bit @ dfa0993, upstream Cloudflare/clef-flash @ 17f0b0a)", "llm": "qwen38 via llama-swap :8090", "git": "0e66557"}.

| measure | value |
|---|---|
| ticks | 277 |
| sim_time_s | 335.9 |
| wall_time_s | 202.3 |
| realtime_factor | 1.66 |
| distance_m | 659.4 |
| battery_end | 83.2 |
| return_reason | corridor complete |
| decisions | 137 |
| decisions_ok | 134 |
| decision_sources | {"CLEF": 119, "FALLBACK": 18, "SAFETY": 1} |
| latency_ms | {"median": 949.05, "p90": 2523.2, "max": 4968.0} |
| photos | 4 |
| recall | 1.0 |
| false_alarms | [] |

## Planted defects against flags

| defect | type | x | found by | Clef's guess | LLM note |
|---|---|---|---|---|---|
| D1 | broken_insulator | 100 | F1 (CLEF) | foreign_object |  |

## Photos

| photo | target x | decided by | action | p(flag) |
|---|---|---|---|---|
| media/photos/photo_01_x040.8.jpg | 41 | CLEF | continue | 0.05 |
| media/photos/photo_02_x050.0.jpg | 50 | CLEF | continue | 0.06 |
| media/photos/photo_03_x100.0.jpg | 100 | CLEF | flag_damage | 0.57 |
| media/photos/photo_04_x200.0.jpg | 200 | CLEF | continue | 0.05 |

Mission log: `m1-clef-seed0-b/mission.jsonl`; frames and photos under `m1-clef-seed0-b/media/` (not in git).
