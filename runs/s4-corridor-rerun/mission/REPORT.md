# Patrol run report: mission

**Result: PASS**

- [x] corridor completed
- [x] returned home
- [x] recall >= 0.5
- [x] false alarms <= 1
- [x] every flag has a photo
- [x] every flag has an LLM note
- [x] Clef decided >= 80% of decisions (measured 98%)

## What ran

Scene `corridor` seed 1, 300 m, 6 planted defects. Versions: {"python": "3.12.14", "mujoco": "3.15.0", "clef": "clef-flash-mlx (mlx-community/clef-flash-8bit @ dfa0993, upstream Cloudflare/clef-flash @ 17f0b0a)", "llm": "qwen38 via llama-swap :8090", "git": "a9ec8eb"}.

Headline: recall 0.833, false alarms 0, LLM on 5.3% of decisions, decision latency median 484.6 ms (p90 649.7), Clef decided 98% of decisions, LLM note names the planted defect type for 5/5 found defects, wall time 83.2 s.

| measure | value |
|---|---|
| ticks | 288 |
| sim_time_s | 216.9 |
| wall_time_s | 83.2 |
| realtime_factor | 2.61 |
| distance_m | 662.8 |
| battery_end | 82.4 |
| return_reason | corridor complete |
| decisions | 132 |
| decisions_ok | 132 |
| decision_sources | {"CLEF": 129, "RANGEFINDER": 1, "OPERATOR": 1, "FALLBACK": 3, "SAFETY": 1} |
| latency_ms | {"median": 484.6, "p90": 649.7, "max": 5130.6} |
| photos | 8 |
| llm_calls | 7 |
| llm_frame_fraction | 0.053 |
| notes_ok | 6 |
| recall | 0.833 |
| false_alarms | [] |

## Planted defects against flags

| defect | type | x | found by | photo triggered by | Clef's guess | LLM note |
|---|---|---|---|---|---|---|
| D1 | vegetation | 20 | F1 (CLEF) | RANGEFINDER | vegetation_close | vegetation, high: A large tree is located immediately adjacent to the phase conductor, with the canopy encroaching on the wire. The rangefinder confirms the tree surface is only  |
| D2 | broken_insulator | 100 | F2 (CLEF) | CLEF | foreign_object | broken_insulator, high: The insulator string is severely damaged with a large gap in the middle of the stack where discs are missing, and a dark, broken fragment is hanging askew from  |
| D3 | frayed_conductor | 130 | F3 (CLEF) | CLEF | conductor_frayed | frayed_conductor, high: The zoomed inspection photo shows a clear cluster of splayed, broken strands on the conductor, resembling a bird's nest or burst wire, which is not present in t |
| D4 | foreign_object | 200 | F5 (CLEF) | CLEF | foreign_object | foreign_object, medium: A large brown object, resembling a bird's nest, is situated on the top surface of the crossarm. The insulator strings and conductors appear intact and free of d |
| D5 | foreign_object | 229 | MISSED |  |  |  |
| D6 | broken_insulator | 250 | F6 (CLEF) | CLEF | foreign_object | broken_insulator, high: The insulator string is missing discs, creating a visible gap in the stack, and a broken disc fragment is hanging askew; additional shattered pieces are visible |

## Photos

| photo | target x | triggered by | decided by | action | p(flag) | clearance m |
|---|---|---|---|---|---|---|
| media/photos/photo_01a_x015.4.jpg | 18 | RANGEFINDER | CLEF | flag_damage | 0.59 | 0.16 |
| media/photos/photo_02a_x015.4.jpg | 18 | OPERATOR | CLEF | flag_damage | 0.64 | 0.17 |
| media/photos/photo_03_x100.0.jpg | 100 | CLEF | CLEF | flag_damage | 0.60 | None |
| media/photos/photo_04a_x121.1.jpg | 124 | CLEF | CLEF | flag_damage | 0.47 | 12.12 |
| media/photos/photo_05a_x131.3.jpg | 134 | CLEF | CLEF | flag_damage | 0.71 | None |
| media/photos/photo_06_x200.0.jpg | 200 | CLEF | CLEF | flag_damage | 0.70 | None |
| media/photos/photo_07_x250.0.jpg | 250 | CLEF | CLEF | flag_damage | 0.75 | None |
| media/photos/photo_08_x300.0.jpg | 300 | CLEF | CLEF | continue | 0.07 | 11.12 |

## Operator commands

- t=13.69: {'name': 'revisit_last_flag'} accepted=True (revisit flag F1 (operator))

Mission log: `mission/mission.jsonl`; frames and photos under `mission/media/` (not in git).
