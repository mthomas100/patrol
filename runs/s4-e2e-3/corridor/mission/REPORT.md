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

Scene `corridor` seed 1, 300 m, 6 planted defects. Versions: {"python": "3.12.14", "mujoco": "3.15.0", "clef": "clef-flash-mlx (mlx-community/clef-flash-8bit @ dfa0993, upstream Cloudflare/clef-flash @ 17f0b0a)", "llm": "qwen38 via llama-swap :8090", "git": "12f7845"}.

Headline: recall 1.0, false alarms 1, LLM on 5.6% of decisions, decision latency median 528.3 ms (p90 829.7), Clef decided 98% of decisions, LLM note names the planted defect type for 6/6 found defects, wall time 117.9 s.

| measure | value |
|---|---|
| ticks | 298 |
| sim_time_s | 255.6 |
| wall_time_s | 117.9 |
| realtime_factor | 2.17 |
| distance_m | 657.4 |
| battery_end | 81.7 |
| return_reason | corridor complete |
| decisions | 144 |
| decisions_ok | 144 |
| decision_sources | {"CLEF": 141, "RANGEFINDER": 1, "OPERATOR": 1, "FALLBACK": 3, "SAFETY": 1} |
| latency_ms | {"median": 528.3, "p90": 829.7, "max": 4541.7} |
| photos | 9 |
| llm_calls | 8 |
| llm_frame_fraction | 0.0556 |
| notes_ok | 7 |
| recall | 1.0 |
| false_alarms | ["F7"] |

## Planted defects against flags

| defect | type | x | found by | photo triggered by | Clef's guess | LLM note |
|---|---|---|---|---|---|---|
| D1 | vegetation | 20 | F1 (CLEF) | RANGEFINDER | vegetation_close | vegetation, high: The zoomed inspection photo shows a tree canopy extremely close to the conductor, with the rangefinder confirming a clearance of only 0.2 m. The conductor itsel |
| D2 | broken_insulator | 100 | F2 (CLEF) | CLEF | foreign_object | broken_insulator, high: The insulator string shows a missing disc in the middle of the stack, creating a visible gap, and a dark object (likely a detached or shattered disc) is hanging |
| D3 | frayed_conductor | 130 | F3 (CLEF) | CLEF | conductor_frayed | frayed_conductor, high: The conductor shows a clear cluster of broken strands splaying outward from the wire body, resembling a bird's nest but consistent with severe fraying. The on-b |
| D4 | foreign_object | 200 | F4 (CLEF) | CLEF | foreign_object | foreign_object, medium: A large brown object, resembling a bird's nest, is resting on top of the upper crossarm. The insulator strings and conductors appear intact and undamaged. |
| D5 | foreign_object | 229 | F5 (CLEF) | CLEF | foreign_object | foreign_object, medium: A large orange rectangular object, resembling a plastic sheet or flag, is entangled on the conductor span between towers 4 and 5. |
| D6 | broken_insulator | 250 | F6 (CLEF) | CLEF | foreign_object | broken_insulator, high: The insulator string is missing discs, creating a visible gap in the middle of the stack, and fragments of shattered glass are scattered on the ground below. A  |

False alarms: F7 at x=262 (note: vegetation)

## Photos

| photo | target x | triggered by | decided by | action | p(flag) | clearance m |
|---|---|---|---|---|---|---|
| media/photos/photo_01a_x016.7.jpg | 20 | RANGEFINDER | CLEF | flag_damage | 0.56 | 0.17 |
| media/photos/photo_02a_x016.7.jpg | 20 | OPERATOR | CLEF | flag_damage | 0.62 | 0.17 |
| media/photos/photo_03_x100.0.jpg | 100 | CLEF | CLEF | flag_damage | 0.33 | None |
| media/photos/photo_04a_x122.4.jpg | 125 | CLEF | CLEF | flag_damage | 0.67 | 12.12 |
| media/photos/photo_05_x200.0.jpg | 200 | CLEF | CLEF | flag_damage | 0.58 | None |
| media/photos/photo_06a_x223.6.jpg | 227 | CLEF | CLEF | flag_damage | 0.24 | 15.4 |
| media/photos/photo_07_x250.0.jpg | 250 | CLEF | CLEF | flag_damage | 0.68 | None |
| media/photos/photo_08a_x258.8.jpg | 262 | CLEF | CLEF | flag_damage | 0.37 | None |
| media/photos/photo_09_x300.0.jpg | 300 | CLEF | CLEF | continue | 0.06 | 11.87 |

## Operator commands

- t=27.44: {'name': 'revisit_last_flag'} accepted=True (revisit flag F1 (operator))

Mission log: `mission/mission.jsonl`; frames and photos under `mission/media/` (not in git).
