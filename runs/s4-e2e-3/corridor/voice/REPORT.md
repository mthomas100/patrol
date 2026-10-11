# Patrol run report: voice

**Result: FAIL**

- [ ] corridor completed
- [x] returned home
- [x] recall >= 0.0
- [x] false alarms <= 99
- [x] every flag has a photo

## What ran

Scene `corridor` seed 1, 300 m, 1 planted defects. Versions: {"python": "3.12.14", "mujoco": "3.15.0", "clef": "clef-flash-mlx (mlx-community/clef-flash-8bit @ dfa0993, upstream Cloudflare/clef-flash @ 17f0b0a)", "llm": "qwen38 via llama-swap :8090", "git": "116bd21"}.

Headline: recall 1.0, false alarms 0, LLM on 0.0% of decisions, decision latency median 457.75 ms (p90 474.4), Clef decided 98% of decisions, LLM note names the planted defect type for 0/1 found defects, wall time 31.1 s.

| measure | value |
|---|---|
| ticks | 141 |
| sim_time_s | 99.8 |
| wall_time_s | 31.1 |
| realtime_factor | 3.21 |
| distance_m | 348.9 |
| battery_end | 91.5 |
| return_reason | operator asked |
| decisions | 60 |
| decisions_ok | 60 |
| decision_sources | {"CLEF": 59, "FALLBACK": 1, "OPERATOR": 1} |
| latency_ms | {"median": 457.75, "p90": 474.4, "max": 1908.2} |
| photos | 1 |
| llm_calls | 0 |
| llm_frame_fraction | 0.0 |
| notes_ok | 0 |
| recall | 1.0 |
| false_alarms | [] |

## Planted defects against flags

| defect | type | x | found by | photo triggered by | Clef's guess | LLM note |
|---|---|---|---|---|---|---|
| D1 | broken_insulator | 100 | F1 (CLEF) | CLEF | insulator_damaged |  |

## Photos

| photo | target x | triggered by | decided by | action | p(flag) | clearance m |
|---|---|---|---|---|---|---|
| media/photos/photo_01_x100.0.jpg | 100 | CLEF | CLEF | flag_damage | 0.76 | None |

## Operator commands

- t=60.33: {'name': 'return_home'} accepted=True (return home (operator))

Mission log: `voice/mission.jsonl`; frames and photos under `voice/media/` (not in git).
