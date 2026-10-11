# Patrol run report: voice

**Result: FAIL**

- [ ] corridor completed
- [x] returned home
- [x] recall >= 0.0
- [x] false alarms <= 99
- [x] every flag has a photo

## What ran

Scene `corridor` seed 1, 300 m, 1 planted defects. Versions: {"python": "3.12.14", "mujoco": "3.15.0", "clef": "clef-flash-mlx (mlx-community/clef-flash-8bit @ dfa0993, upstream Cloudflare/clef-flash @ 17f0b0a)", "llm": "qwen38 via llama-swap :8090", "git": "f4ddd15"}.

Headline: recall 1.0, false alarms 0, LLM on 0.0% of decisions, decision latency median 406.4 ms (p90 412.4), Clef decided 100% of decisions, LLM note names the planted defect type for 0/1 found defects, wall time 26.7 s.

| measure | value |
|---|---|
| ticks | 139 |
| sim_time_s | 94.1 |
| wall_time_s | 26.7 |
| realtime_factor | 3.52 |
| distance_m | 327.3 |
| battery_end | 91.6 |
| return_reason | operator asked |
| decisions | 60 |
| decisions_ok | 60 |
| decision_sources | {"CLEF": 60, "OPERATOR": 1} |
| latency_ms | {"median": 406.4, "p90": 412.4, "max": 622.7} |
| photos | 1 |
| llm_calls | 0 |
| llm_frame_fraction | 0.0 |
| notes_ok | 0 |
| recall | 1.0 |
| false_alarms | [] |

## Planted defects against flags

| defect | type | x | found by | photo triggered by | Clef's guess | LLM note |
|---|---|---|---|---|---|---|
| D1 | broken_insulator | 100 | F1 (CLEF) | CLEF | foreign_object |  |

## Photos

| photo | target x | triggered by | decided by | action | p(flag) | clearance m |
|---|---|---|---|---|---|---|
| media/photos/photo_01_x100.0.jpg | 100 | CLEF | CLEF | flag_damage | 0.72 | None |

## Operator commands

- t=55.58: {'name': 'return_home'} accepted=True (return home (operator))

Mission log: `voice/mission.jsonl`; frames and photos under `voice/media/` (not in git).
