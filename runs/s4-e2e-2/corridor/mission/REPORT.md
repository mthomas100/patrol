# Patrol run report: mission

**Result: FAIL**

- [x] corridor completed
- [x] returned home
- [x] recall >= 0.5
- [ ] false alarms <= 1
- [x] every flag has a photo
- [x] every flag has an LLM note
- [x] Clef decided >= 80% of decisions (measured 98%)

## What ran

Scene `corridor` seed 1, 300 m, 6 planted defects. Versions: {"python": "3.12.14", "mujoco": "3.15.0", "clef": "clef-flash-mlx (mlx-community/clef-flash-8bit @ dfa0993, upstream Cloudflare/clef-flash @ 17f0b0a)", "llm": "qwen38 via llama-swap :8090", "git": "a9ec8eb"}.

Headline: recall 0.833, false alarms 2, LLM on 5.6% of decisions, decision latency median 460.6 ms (p90 865.0), Clef decided 98% of decisions, LLM note names the planted defect type for 5/5 found defects, wall time 107.8 s.

| measure | value |
|---|---|
| ticks | 296 |
| sim_time_s | 244.4 |
| wall_time_s | 107.8 |
| realtime_factor | 2.27 |
| distance_m | 660.9 |
| battery_end | 81.9 |
| return_reason | corridor complete |
| decisions | 142 |
| decisions_ok | 142 |
| decision_sources | {"CLEF": 139, "RANGEFINDER": 2, "OPERATOR": 1, "FALLBACK": 3, "SAFETY": 1} |
| latency_ms | {"median": 460.6, "p90": 865.0, "max": 4722.8} |
| photos | 9 |
| llm_calls | 8 |
| llm_frame_fraction | 0.0563 |
| notes_ok | 7 |
| recall | 0.833 |
| false_alarms | ["F1", "F7"] |

## Planted defects against flags

| defect | type | x | found by | photo triggered by | Clef's guess | LLM note |
|---|---|---|---|---|---|---|
| D1 | vegetation | 20 | F2 (CLEF) | RANGEFINDER | vegetation_close | vegetation, high: The rangefinder confirms a tree is extremely close to the conductor (0.2 m), which is well within the 1 m safety clearance limit. The visual inspection shows th |
| D2 | broken_insulator | 100 | F3 (CLEF) | CLEF | foreign_object | broken_insulator, high: The insulator string is missing discs compared to the reference photo, and a dark, broken fragment is hanging askew in the middle of the stack with additional d |
| D3 | frayed_conductor | 130 | F4 (CLEF) | CLEF | conductor_frayed | frayed_conductor, high: The inspection photo clearly shows a cluster of splayed, broken strands on the conductor, resembling a bird's nest or burst wire, which is distinct from the smo |
| D4 | foreign_object | 200 | F5 (CLEF) | CLEF | foreign_object | foreign_object, medium: A large brown object, resembling a bird's nest, is resting on top of the crossarm. The insulator strings and conductors appear intact and free of damage. |
| D5 | foreign_object | 229 | MISSED |  |  |  |
| D6 | broken_insulator | 250 | F6 (CLEF) | CLEF | foreign_object | broken_insulator, high: The insulator string is severely damaged with a large gap in the middle of the stack where discs are missing, and a dark fragment is hanging askew; several shat |

False alarms: F1 at x=18 (note: vegetation), F7 at x=261 (note: vegetation)

## Photos

| photo | target x | triggered by | decided by | action | p(flag) | clearance m |
|---|---|---|---|---|---|---|
| media/photos/photo_01a_x014.6.jpg | 18 | RANGEFINDER | CLEF | flag_damage | 0.75 | 0.07 |
| media/photos/photo_02a_x016.1.jpg | 19 | RANGEFINDER | CLEF | flag_damage | 0.53 | 0.17 |
| media/photos/photo_03a_x016.1.jpg | 19 | OPERATOR | CLEF | flag_damage | 0.53 | 0.17 |
| media/photos/photo_04_x100.0.jpg | 100 | CLEF | CLEF | flag_damage | 0.75 | None |
| media/photos/photo_05a_x122.9.jpg | 126 | CLEF | CLEF | flag_damage | 0.64 | 12.28 |
| media/photos/photo_06_x200.0.jpg | 200 | CLEF | CLEF | flag_damage | 0.64 | None |
| media/photos/photo_07_x250.0.jpg | 250 | CLEF | CLEF | flag_damage | 0.66 | None |
| media/photos/photo_08a_x258.3.jpg | 261 | CLEF | CLEF | flag_damage | 0.31 | None |
| media/photos/photo_09_x300.0.jpg | 300 | CLEF | CLEF | continue | 0.06 | 11.16 |

## Operator commands

- t=26.52: {'name': 'revisit_last_flag'} accepted=True (revisit flag F2 (operator))

Mission log: `mission/mission.jsonl`; frames and photos under `mission/media/` (not in git).
