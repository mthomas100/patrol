# Patrol run report: mission

**Result: FAIL**

- [x] corridor completed
- [x] returned home
- [x] recall >= 0.5
- [ ] false alarms <= 1
- [x] every flag has a photo
- [x] every flag has an LLM note
- [x] Clef decided >= 80% of decisions (measured 97%)

## What ran

Scene `corridor` seed 1, 300 m, 6 planted defects. Versions: {"python": "3.12.14", "mujoco": "3.15.0", "clef": "clef-flash-mlx (mlx-community/clef-flash-8bit @ dfa0993, upstream Cloudflare/clef-flash @ 17f0b0a)", "llm": "qwen38 via llama-swap :8090", "git": "beb35c2"}.

Headline: recall 0.833, false alarms 2, LLM on 5.6% of decisions, decision latency median 463.1 ms (p90 807.3), Clef decided 97% of decisions, LLM note names the planted defect type for 5/5 found defects, wall time 106.4 s.

| measure | value |
|---|---|
| ticks | 297 |
| sim_time_s | 243.6 |
| wall_time_s | 106.4 |
| realtime_factor | 2.29 |
| distance_m | 660.7 |
| battery_end | 81.8 |
| return_reason | corridor complete |
| decisions | 142 |
| decisions_ok | 142 |
| decision_sources | {"CLEF": 138, "RANGEFINDER": 2, "OPERATOR": 1, "FALLBACK": 4, "SAFETY": 1} |
| latency_ms | {"median": 463.1, "p90": 807.3, "max": 4972.8} |
| photos | 9 |
| llm_calls | 8 |
| llm_frame_fraction | 0.0563 |
| notes_ok | 7 |
| recall | 0.833 |
| false_alarms | ["F1", "F7"] |

## Planted defects against flags

| defect | type | x | found by | photo triggered by | Clef's guess | LLM note |
|---|---|---|---|---|---|---|
| D1 | vegetation | 20 | F2 (CLEF) | RANGEFINDER | vegetation_close | vegetation, high: The rangefinder confirms a tree is extremely close to the conductor (0.2 m), which is well within the 1 m safety limit. The visual inspection shows no damage to |
| D2 | broken_insulator | 100 | F3 (CLEF) | CLEF | foreign_object | broken_insulator, high: The near-phase insulator string is severely damaged, with a large gap in the middle of the stack where discs are missing and a dark, broken disc hanging askew.  |
| D3 | frayed_conductor | 130 | F4 (CLEF) | CLEF | conductor_frayed | frayed_conductor, high: The conductor shows a distinct cluster of splayed, broken strands (birdcaging) at the mid-span point, clearly visible against the background. The on-board model |
| D4 | foreign_object | 200 | F5 (CLEF) | CLEF | foreign_object | foreign_object, low: A brown, oval-shaped object with protruding spikes (resembling a nest or burr) is resting on the top surface of the crossarm. The insulator strings and conducto |
| D5 | foreign_object | 229 | MISSED |  |  |  |
| D6 | broken_insulator | 250 | F6 (CLEF) | CLEF | foreign_object | broken_insulator, high: The insulator string is missing multiple discs, creating a large gap in the middle of the stack, and fragments of broken discs are visible falling below the str |

False alarms: F1 at x=17 (note: vegetation), F7 at x=263 (note: vegetation)

## Photos

| photo | target x | triggered by | decided by | action | p(flag) | clearance m |
|---|---|---|---|---|---|---|
| media/photos/photo_01a_x014.4.jpg | 17 | RANGEFINDER | CLEF | flag_damage | 0.74 | 0.09 |
| media/photos/photo_02a_x015.9.jpg | 19 | RANGEFINDER | CLEF | flag_damage | 0.57 | 0.17 |
| media/photos/photo_03a_x015.9.jpg | 19 | OPERATOR | CLEF | flag_damage | 0.57 | 0.17 |
| media/photos/photo_04_x100.0.jpg | 100 | CLEF | CLEF | flag_damage | 0.60 | None |
| media/photos/photo_05a_x121.1.jpg | 124 | CLEF | CLEF | flag_damage | 0.60 | 12.11 |
| media/photos/photo_06_x200.0.jpg | 200 | CLEF | CLEF | flag_damage | 0.63 | None |
| media/photos/photo_07_x250.0.jpg | 250 | CLEF | CLEF | flag_damage | 0.78 | None |
| media/photos/photo_08a_x259.9.jpg | 263 | CLEF | CLEF | flag_damage | 0.37 | None |
| media/photos/photo_09_x300.0.jpg | 300 | CLEF | CLEF | continue | 0.06 | 11.23 |

## Operator commands

- t=25.9: {'name': 'revisit_last_flag'} accepted=True (revisit flag F2 (operator))

Mission log: `mission/mission.jsonl`; frames and photos under `mission/media/` (not in git).
