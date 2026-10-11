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

Scene `corridor` seed 2, 300 m, 6 planted defects. Versions: {"python": "3.12.14", "mujoco": "3.15.0", "clef": "clef-flash-mlx (mlx-community/clef-flash-8bit @ dfa0993, upstream Cloudflare/clef-flash @ 17f0b0a)", "llm": "qwen38 via llama-swap :8090", "git": "f4ddd15"}.

Headline: recall 0.833, false alarms 1, LLM on 6.2% of decisions, decision latency median 499.85 ms (p90 765.8), Clef decided 98% of decisions, LLM note names the planted defect type for 5/5 found defects, wall time 81.3 s.

| measure | value |
|---|---|
| ticks | 286 |
| sim_time_s | 213.6 |
| wall_time_s | 81.3 |
| realtime_factor | 2.63 |
| distance_m | 665.0 |
| battery_end | 82.5 |
| return_reason | corridor complete |
| decisions | 130 |
| decisions_ok | 130 |
| decision_sources | {"CLEF": 127, "RANGEFINDER": 1, "FALLBACK": 3, "OPERATOR": 1, "SAFETY": 1} |
| latency_ms | {"median": 499.85, "p90": 765.8, "max": 1763.0} |
| photos | 8 |
| llm_calls | 8 |
| llm_frame_fraction | 0.0615 |
| notes_ok | 7 |
| recall | 0.833 |
| false_alarms | ["F3"] |

## Planted defects against flags

| defect | type | x | found by | photo triggered by | Clef's guess | LLM note |
|---|---|---|---|---|---|---|
| D1 | vegetation | 32 | F1 (CLEF) | RANGEFINDER | vegetation_close | vegetation, high: The inspection photos show a tree canopy in immediate proximity to the phase conductor, with the rangefinder confirming a clearance of only 0.1 m. The conductor |
| D2 | broken_insulator | 100 | F2 (CLEF) | CLEF | foreign_object | broken_insulator, high: The inspection photo shows a dark, jagged object attached to the middle of the insulator stack, which is not present on the healthy reference string. Additional |
| D3 | frayed_conductor | 132 | F4 (CLEF) | CLEF | foreign_object | frayed_conductor, high: The inspection photo shows a clear defect on the conductor where the outer strands are broken and splayed outwards, resembling a burst or bird's nest shape. Thi |
| D4 | foreign_object | 200 | F6 (CLEF) | CLEF | foreign_object | foreign_object, medium: A large brown object resembling a bird's nest is resting on top of the crossarm. The insulator strings and conductors appear intact and match the reference desi |
| D5 | foreign_object | 218 | MISSED |  |  |  |
| D6 | broken_insulator | 250 | F7 (CLEF) | CLEF | foreign_object | broken_insulator, high: The insulator string is severely damaged with a large gap in the middle of the stack and a dark, broken component hanging askew; fragments of the shattered disc |

False alarms: F3 at x=116 (note: vegetation)

## Photos

| photo | target x | triggered by | decided by | action | p(flag) | clearance m |
|---|---|---|---|---|---|---|
| media/photos/photo_01a_x027.5.jpg | 31 | RANGEFINDER | CLEF | flag_damage | 0.73 | 0.06 |
| media/photos/photo_02a_x027.5.jpg | 31 | OPERATOR | CLEF | flag_damage | 0.72 | 0.07 |
| media/photos/photo_03_x100.0.jpg | 100 | CLEF | CLEF | flag_damage | 0.77 | None |
| media/photos/photo_04a_x112.5.jpg | 116 | CLEF | CLEF | flag_damage | 0.28 | None |
| media/photos/photo_05a_x121.8.jpg | 125 | CLEF | CLEF | flag_damage | 0.46 | None |
| media/photos/photo_06a_x132.4.jpg | 135 | CLEF | CLEF | flag_damage | 0.21 | 10.95 |
| media/photos/photo_07_x200.0.jpg | 200 | CLEF | CLEF | flag_damage | 0.64 | None |
| media/photos/photo_08_x250.0.jpg | 250 | CLEF | CLEF | flag_damage | 0.73 | None |

## Operator commands

- t=16.95: {'name': 'revisit_last_flag'} accepted=True (revisit flag F1 (operator))

Mission log: `mission/mission.jsonl`; frames and photos under `mission/media/` (not in git).
