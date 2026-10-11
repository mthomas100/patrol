# Patrol search e2e: s4-e2e-4

**Result: FAIL**

Command: `tests/e2e_search.sh --only 1,2,3,4,5,6 --with-corridor`; total wall time 646 s. Versions: {"python": "3.12.14", "mujoco": "3.15.0", "clef": "clef-flash-mlx (mlx-community/clef-flash-8bit @ dfa0993, upstream Cloudflare/clef-flash @ 17f0b0a)", "llm": "qwen38 via llama-swap :8090", "git": "beb35c2"}.

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
- [x] S5: flight ended at home (area covered)
- [x] S5: every clue found (4/4; missed [])
- [x] S5: no duplicate alerts ([])
- [x] S5: no false alert ([])
- [x] S6: heard "Missing hiker, blue backpack, orange tent, gray dog."; qwen38's clue options name ['blue_backpack', 'orange_tent', 'grey_dog'] of ['blue_backpack', 'orange_tent', 'grey_dog'] (['blue_backpack', 'orange_tent', 'gray_dog'])
- [x] S6: every alert read aloud (['A1', 'A2'] of ['A1', 'A2'])
- [x] S6: 'go back to the last alert' heard, routed and executed ([('Go back to the last alert.', 'go_back_to_last_alert', 'CLEF'), ('Stop searching and come home.', 'return_home', 'CLEF')])
- [x] S6: 'stop searching and come home' executed, flight ended at home (operator: return home)
- [x] S6: no false alert ([])
- [ ] power-line regression e2e passes (corridor/REPORT.md)

## Metrics

| scenario | recall | false alerts | first find s | loc err m | covered | m² per battery | frames | Clef calls | LLM calls | alerts/candidates | investigations (mean s, decision h) | sweep ms p50/p90 | confirm ms p50/p90 | Clef ms, qwen38 idle | Clef ms, qwen38 busy | qwen38 calls by role | sim s | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 item present | 1/1 | 0 | 186.66 | [0.04] | 100% | 108017 | 101 | 160 (1.58/frame) | 2 | 1/303 | 1 (7.3 s, 20.0 m) | 223/272 | 350/350 | 219/246 (n 137) | 278/341 (n 23) | {'note': 1, 'trail': 1} | 426.9 | 44.7 |
| 2 decoys | 0/0 | 0 | None | [] | 100% | 113778 | 97 | 158 (1.63/frame) | 0 | 0/291 | 2 (8.5 s, 20.0 m) | 372/395 | 490/466 | 372/404 (n 158) | None/None (n 0) | {} | 405.1 | 66.3 |
| 3 empty | 0/0 | 0 | None | [] | 100% | 103226 | 99 | 163 (1.65/frame) | 0 | 0/297 | 3 (8.8 s, 20.0 m) | 327/359 | 420/420 | 328/377 (n 163) | None/None (n 0) | {} | 447.2 | 61.5 |
| 4 Clef off | 0/1 | 0 | None | [] | 100% | 96154 | 41 | 123 (3.00/frame) | 0 | 0/123 | 0 (None s, None m) | None/None | None/None | None/None (n 123) | None/None (n 0) | {} | 187.6 | 3.0 |
| 5 several | 4/4 | 0 | 201.27 | [0.05, 0.61, 0.03, 0.01] | 100% | 35655 | 354 | 494 (1.40/frame) | 12 | 4/1062 | 25 (7.8 s, 18.1 m) | 373/441 | 484/609 | 370/412 (n 423) | 454/603 (n 71) | {'note': 4, 'trail': 4, 'second_opinion': 4} | 1293.5 | 228.2 |
| 6 voice | 2/3 | 0 | 35.4 | [0.23, 0.03] | 29% | 69211 | 28 | 49 (1.75/frame) | 4 | 2/84 | 3 (7.1 s, 20.0 m) | 363/492 | 518/518 | 322/361 (n 24) | 390/659 (n 25) | {'note': 2, 'trail': 2} | 196.0 | 25.3 |

## Steps

| step | wall s | detail |
|---|---|---|
| offline tests | 1.3 | `70 passed in 1.17s` |
| S1 item present | 45.1 | `search --terrain grass --seed 21 --items grey_dog,grey_boulder --clues grey_dog --out runs/s4-e2e-4/s1 --think` |
| S2 decoys | 66.7 | `search --terrain snow --seed 22 --items blue_tarp,red_rock,orange_leaf_pile,grey_boulder --clues blue_backpack,red_jacket,orange_tent,grey_dog --out runs/s4-e2e-4/s2 --think` |
| S3 empty | 61.8 | `search --terrain grass --seed 23 --items  --clues blue_backpack,orange_tent,grey_dog --out runs/s4-e2e-4/s3 --think` |
| S4 Clef off | 3.4 | `search --terrain snow --seed 24 --items blue_backpack --clues blue_backpack --out runs/s4-e2e-4/s4 --clef-url http://127.0.0.1:9/v1/systemone --half 50 --think` |
| S5 several | 228.7 | `search --terrain snow --seed 45 --items grey_dog,green_sleeping_bag,yellow_helmet,sos_rocks,grey_boulder,orange_leaf_pile --clues grey_dog,green_sleeping_bag,yellow_helmet,sos_rocks --out runs/s4-e2e-4/s5 --think` |
| S6 voice | 38.9 | `search --terrain grass --seed 26 --items blue_backpack,orange_tent,grey_dog,blue_tarp --clues blue_backpack,orange_tent,grey_dog --out runs/s4-e2e-4/s6 --describe-wav fixtures/voice/describe_demo.wav --speak --voice-script {"alert:1": "fixtures/voice/go_back_alert.wav", "alert:2": "fixtures/voice/return_home_search.wav"} --think` |
| corridor regression (seed 1) | 199.2 | `patrol.e2e --seed 1` |

## Preflight

```
{
 "clef_ok": true,
 "clef_wait_s": 0.0,
 "hold_status": "open: model calls pass; qwen38 (ready) loaded",
 "memory_free": "System-wide memory free percentage: 32%",
 "qwen38": "ok: OK",
 "qwen38_s": 0.4
}
```
