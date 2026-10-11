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

Scene `corridor` seed 0, 300 m, 6 planted defects. Versions: {"python": "3.12.14", "mujoco": "3.15.0", "clef": "clef-flash-mlx (mlx-community/clef-flash-8bit @ dfa0993, upstream Cloudflare/clef-flash @ 17f0b0a)", "llm": "qwen38 via llama-swap :8090", "git": "f4ddd15"}.

Headline: recall 0.833, false alarms 1, LLM on 5.3% of decisions, decision latency median 496.0 ms (p90 712.1), Clef decided 98% of decisions, LLM note names the planted defect type for 4/5 found defects, wall time 79.7 s.

| measure | value |
|---|---|
| ticks | 288 |
| sim_time_s | 213.4 |
| wall_time_s | 79.7 |
| realtime_factor | 2.68 |
| distance_m | 663.8 |
| battery_end | 82.3 |
| return_reason | corridor complete |
| decisions | 131 |
| decisions_ok | 131 |
| decision_sources | {"CLEF": 129, "RANGEFINDER": 1, "OPERATOR": 1, "FALLBACK": 2, "SAFETY": 1} |
| latency_ms | {"median": 496.0, "p90": 712.1, "max": 1898.7} |
| photos | 9 |
| llm_calls | 7 |
| llm_frame_fraction | 0.0534 |
| notes_ok | 6 |
| recall | 0.833 |
| false_alarms | ["F4"] |

## Planted defects against flags

| defect | type | x | found by | photo triggered by | Clef's guess | LLM note |
|---|---|---|---|---|---|---|
| D1 | vegetation | 30 | F1 (CLEF) | RANGEFINDER | vegetation_close | vegetation, high: A large tree is located immediately adjacent to the phase conductor, with the lidar confirming a clearance of only 0.1 m. The conductor passes directly through  |
| D2 | broken_insulator | 100 | F2 (CLEF) | CLEF | foreign_object | broken_insulator, high: The insulator string is severely damaged with a large gap in the middle of the stack where discs are missing, and a dark, broken component is hanging askew. Deb |
| D3 | frayed_conductor | 129 | F3 (CLEF) | CLEF | foreign_object | foreign_object, medium: A foreign object consisting of a cluster of sticks or branches is entangled on the conductor, located near a tree. The object appears to be caught on a splice o |
| D4 | foreign_object | 200 | F5 (CLEF) | CLEF | foreign_object | foreign_object, low: A brown, oval-shaped object resembling a large nest or debris is resting on the top surface of the crossarm. The insulator strings appear intact with no visible |
| D5 | foreign_object | 224 | MISSED |  |  |  |
| D6 | broken_insulator | 250 | F6 (CLEF) | CLEF | insulator_damaged | broken_insulator, high: The insulator string is damaged with a missing or shattered disc in the middle of the stack, and fragments of the broken disc are visible falling below the stri |

False alarms: F4 at x=165 (note: vegetation)

## Photos

| photo | target x | triggered by | decided by | action | p(flag) | clearance m |
|---|---|---|---|---|---|---|
| media/photos/photo_01a_x026.6.jpg | 30 | RANGEFINDER | CLEF | flag_damage | 0.75 | 0.07 |
| media/photos/photo_02a_x026.6.jpg | 30 | OPERATOR | CLEF | flag_damage | 0.72 | 0.07 |
| media/photos/photo_03_x100.0.jpg | 100 | CLEF | CLEF | flag_damage | 0.73 | None |
| media/photos/photo_04a_x117.1.jpg | 120 | CLEF | CLEF | continue | 0.17 | None |
| media/photos/photo_05a_x127.2.jpg | 130 | CLEF | CLEF | flag_damage | 0.59 | None |
| media/photos/photo_06a_x162.2.jpg | 165 | CLEF | CLEF | flag_damage | 0.47 | None |
| media/photos/photo_07a_x173.8.jpg | 177 | CLEF | CLEF | continue | 0.10 | 7.79 |
| media/photos/photo_08_x200.0.jpg | 200 | CLEF | CLEF | flag_damage | 0.59 | None |
| media/photos/photo_09_x250.0.jpg | 250 | CLEF | CLEF | flag_damage | 0.75 | None |

## Operator commands

- t=17.29: {'name': 'revisit_last_flag'} accepted=True (revisit flag F1 (operator))

Mission log: `mission/mission.jsonl`; frames and photos under `mission/media/` (not in git).
