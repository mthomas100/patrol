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

Scene `corridor` seed 1, 300 m, 6 planted defects. Versions: {"python": "3.12.14", "mujoco": "3.15.0", "clef": "clef-flash-mlx (mlx-community/clef-flash-8bit @ dfa0993, upstream Cloudflare/clef-flash @ 17f0b0a)", "llm": "qwen38 via llama-swap :8090", "git": "f4ddd15"}.

Headline: recall 0.833, false alarms 0, LLM on 5.5% of decisions, decision latency median 501.15 ms (p90 727.8), Clef decided 98% of decisions, LLM note names the planted defect type for 4/5 found defects, wall time 78.0 s.

| measure | value |
|---|---|
| ticks | 282 |
| sim_time_s | 208.8 |
| wall_time_s | 78.0 |
| realtime_factor | 2.68 |
| distance_m | 660.5 |
| battery_end | 82.7 |
| return_reason | corridor complete |
| decisions | 128 |
| decisions_ok | 128 |
| decision_sources | {"CLEF": 125, "RANGEFINDER": 1, "OPERATOR": 1, "FALLBACK": 3, "SAFETY": 1} |
| latency_ms | {"median": 501.15, "p90": 727.8, "max": 1196.5} |
| photos | 8 |
| llm_calls | 7 |
| llm_frame_fraction | 0.0547 |
| notes_ok | 6 |
| recall | 0.833 |
| false_alarms | [] |

## Planted defects against flags

| defect | type | x | found by | photo triggered by | Clef's guess | LLM note |
|---|---|---|---|---|---|---|
| D1 | vegetation | 20 | F1 (CLEF) | RANGEFINDER | vegetation_close | vegetation, high: A tree is located immediately adjacent to the phase conductor, with the rangefinder confirming a clearance of only 0.2 m. The conductor itself appears intact wi |
| D2 | broken_insulator | 100 | F2 (CLEF) | CLEF | foreign_object | broken_insulator, high: The near-phase insulator string is missing several discs compared to the reference, leaving a large gap in the middle of the stack. A dark, detached component i |
| D3 | frayed_conductor | 130 | F3 (CLEF) | CLEF | foreign_object | foreign_object, medium: A spiky, star-shaped foreign object (resembling a kite frame or debris) is entangled on the conductor span between towers 2 and 3. The on-board model's 'frayed_ |
| D4 | foreign_object | 200 | F5 (CLEF) | CLEF | foreign_object | foreign_object, low: A brown, oval-shaped object with protruding spikes (resembling a nest or burr) is resting on the top surface of the crossarm. The insulator strings below appear |
| D5 | foreign_object | 229 | MISSED |  |  |  |
| D6 | broken_insulator | 250 | F6 (CLEF) | CLEF | foreign_object | broken_insulator, high: The insulator string is missing multiple discs, creating a large gap in the middle of the stack, and there are dark fragments visible on the ground below the to |

## Photos

| photo | target x | triggered by | decided by | action | p(flag) | clearance m |
|---|---|---|---|---|---|---|
| media/photos/photo_01a_x016.6.jpg | 20 | RANGEFINDER | CLEF | flag_damage | 0.55 | 0.17 |
| media/photos/photo_02a_x016.6.jpg | 20 | OPERATOR | CLEF | flag_damage | 0.65 | 0.17 |
| media/photos/photo_03_x100.0.jpg | 100 | CLEF | CLEF | flag_damage | 0.54 | None |
| media/photos/photo_04a_x121.1.jpg | 124 | CLEF | CLEF | flag_damage | 0.38 | 12.12 |
| media/photos/photo_05a_x130.7.jpg | 134 | CLEF | CLEF | flag_damage | 0.62 | 9.56 |
| media/photos/photo_06_x200.0.jpg | 200 | CLEF | CLEF | flag_damage | 0.73 | None |
| media/photos/photo_07_x250.0.jpg | 250 | CLEF | CLEF | flag_damage | 0.76 | None |
| media/photos/photo_08_x300.0.jpg | 300 | CLEF | CLEF | continue | 0.06 | 11.12 |

## Operator commands

- t=14.26: {'name': 'revisit_last_flag'} accepted=True (revisit flag F1 (operator))

Mission log: `mission/mission.jsonl`; frames and photos under `mission/media/` (not in git).
