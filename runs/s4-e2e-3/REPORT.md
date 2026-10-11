# Patrol search e2e: s4-e2e-3

**Result: PASS**

Command: `tests/e2e_search.sh --only 1,2,3,4,5,6 --with-corridor`; total wall time 670 s. Versions: {"python": "3.12.14", "mujoco": "3.15.0", "clef": "clef-flash-mlx (mlx-community/clef-flash-8bit @ dfa0993, upstream Cloudflare/clef-flash @ 17f0b0a)", "llm": "qwen38 via llama-swap :8090", "git": "116bd21"}.

Held-out items: grey_dog, green_sleeping_bag, yellow_helmet, sos_rocks (never used for tuning). Decoys: grey_boulder, red_rock, orange_leaf_pile, blue_tarp. Scenario 6 (voice) uses tuning items plus the grey dog and qwen38's own clue wording from the spoken description. Thresholds and rules: DECISIONS 2026-10-11 (patrol-aa, patrol-5d); the e2e pass bars are justified in DECISIONS 2026-10-11 patrol-5d (S4).

## Checks

- [x] offline tests pass
- [x] S1: flight ended at home (area covered)
- [x] S1: grey_dog noticed by the finder (1 of 1 frames in view)
- [x] S1: investigated (1) and alerted with the right clue
- [x] S1: alert within 5 m (error 0.04 m)
- [x] S1: no false alert ([])
- [x] S2: flight ended at home (area covered)
- [x] S2: no alert (got []; decoys investigated 2)
- [x] S2: area covered (100%)
- [x] S3: flight ended at home (area covered)
- [x] S3: no alert (got []; decoys investigated 0)
- [x] S3: area covered (100%)
- [x] S4: flight ended at home (area covered)
- [x] S4: every answer was FALLBACK (123 of 123)
- [x] S4: the sweep finished (100% covered, area covered)
- [x] S4: no alert
- [x] S5: flight ended at home (battery 15% leaves only the return reserve)
- [x] S5: every clue found (4/4; missed [])
- [x] S5: no duplicate alerts ([])
- [x] S5: no false alert ([])
- [x] S6: heard "Missing hiker, blue backpack, orange tent, gray dog."; qwen38's clue options name ['blue_backpack', 'orange_tent', 'grey_dog'] of ['blue_backpack', 'orange_tent', 'grey_dog'] (['blue_backpack', 'orange_tent', 'gray_dog'])
- [x] S6: every alert read aloud (['A1', 'A2'] of ['A1', 'A2'])
- [x] S6: 'go back to the last alert' heard, routed and executed ([('Go back to the last alert.', 'go_back_to_last_alert', 'CLEF'), ('Stop searching and come home.', 'return_home', 'CLEF')])
- [x] S6: 'stop searching and come home' executed, flight ended at home (operator: return home)
- [x] S6: no false alert ([])
- [x] power-line regression e2e passes (corridor/REPORT.md)

## Metrics

| scenario | recall | false alerts | first find s | loc err m | covered | m² per battery | frames | Clef calls | LLM calls | alerts/candidates | investigations (mean s, decision h) | sweep ms p50/p90 | confirm ms p50/p90 | Clef ms, qwen38 idle | Clef ms, qwen38 busy | qwen38 calls by role | sim s | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 item present | 1/1 | 0 | 191.85 | [0.04] | 100% | 74419 | 100 | 161 (1.61/frame) | 2 | 1/300 | 1 (9.1 s, 20.0 m) | 236/275 | 2142/2142 | 234/245 (n 140) | 301/379 (n 21) | {'note': 1, 'trail': 1} | 413.8 | 50.0 |
| 2 decoys | 0/0 | 0 | None | [] | 100% | 67016 | 99 | 158 (1.60/frame) | 0 | 0/297 | 2 (9.6 s, 20.0 m) | 389/411 | 1622/571 | 390/412 (n 158) | None/None (n 0) | {} | 458.9 | 72.8 |
| 3 empty | 0/0 | 0 | None | [] | 100% | 71709 | 100 | 165 (1.65/frame) | 0 | 0/300 | 3 (8.6 s, 20.0 m) | 343/381 | 459/459 | 343/386 (n 165) | None/None (n 0) | {} | 428.4 | 67.8 |
| 4 Clef off | 0/1 | 0 | None | [] | 100% | 64103 | 41 | 123 (3.00/frame) | 0 | 0/123 | 0 (None s, None m) | None/None | None/None | None/None (n 123) | None/None (n 0) | {} | 187.5 | 3.0 |
| 5 several | 4/4 | 0 | 202.29 | [0.01, 0.05, 0.01, 0.01] | 97% | 28005 | 296 | 440 (1.49/frame) | 11 | 4/888 | 25 (7.9 s, 18.7 m) | 385/465 | 514/725 | 384/436 (n 378) | 489/674 (n 62) | {'second_opinion': 3, 'note': 4, 'trail': 4} | 1059.6 | 215.5 |
| 6 voice | 2/3 | 0 | 38.72 | [0.58, 0.03] | 27% | 42925 | 26 | 47 (1.81/frame) | 4 | 2/78 | 3 (7.7 s, 20.0 m) | 357/554 | 1112/1112 | 342/410 (n 30) | 503/1112 (n 17) | {'note': 2, 'trail': 2} | 193.0 | 30.8 |

## Steps

| step | wall s | detail |
|---|---|---|
| offline tests | 1.4 | `70 passed in 1.26s` |
| S1 item present | 50.4 | `search --terrain grass --seed 21 --items grey_dog,grey_boulder --clues grey_dog --out runs/s4-e2e-3/s1 --think` |
| S2 decoys | 73.2 | `search --terrain snow --seed 22 --items blue_tarp,red_rock,orange_leaf_pile,grey_boulder --clues blue_backpack,red_jacket,orange_tent,grey_dog --out runs/s4-e2e-3/s2 --think` |
| S3 empty | 68.1 | `search --terrain grass --seed 23 --items  --clues blue_backpack,orange_tent,grey_dog --out runs/s4-e2e-3/s3 --think` |
| S4 Clef off | 3.4 | `search --terrain snow --seed 24 --items blue_backpack --clues blue_backpack --out runs/s4-e2e-3/s4 --clef-url http://127.0.0.1:9/v1/systemone --half 50 --think` |
| S5 several | 216.4 | `search --terrain snow --seed 45 --items grey_dog,green_sleeping_bag,yellow_helmet,sos_rocks,grey_boulder,orange_leaf_pile --clues grey_dog,green_sleeping_bag,yellow_helmet,sos_rocks --out runs/s4-e2e-3/s5 --think` |
| S6 voice | 37.1 | `search --terrain grass --seed 26 --items blue_backpack,orange_tent,grey_dog,blue_tarp --clues blue_backpack,orange_tent,grey_dog --out runs/s4-e2e-3/s6 --describe-wav fixtures/voice/describe_demo.wav --speak --voice-script {"alert:1": "fixtures/voice/go_back_alert.wav", "alert:2": "fixtures/voice/return_home_search.wav"} --think` |
| corridor regression (seed 1) | 219.3 | `patrol.e2e --seed 1` |

## Preflight

```
{
 "clef_ok": true,
 "clef_wait_s": 0.0,
 "hold_status": "open: model calls pass; qwen38 (ready) loaded",
 "memory_free": "System-wide memory free percentage: 22%",
 "qwen38": "ok: OK",
 "qwen38_s": 0.4
}
```
