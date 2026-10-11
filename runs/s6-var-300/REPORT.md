# Patrol search e2e: s6-var-300

**Result: FAIL**

Command: `tests/e2e_search.sh --only 1,2,3,4,5,6`; total wall time 447 s. Versions: {"python": "3.12.14", "mujoco": "3.15.0", "clef": "clef-flash-mlx (mlx-community/clef-flash-8bit @ dfa0993, upstream Cloudflare/clef-flash @ 17f0b0a)", "llm": "qwen38 via llama-swap :8090", "git": "90e71c8"}.

Held-out items: grey_dog, green_sleeping_bag, yellow_helmet, sos_rocks (never used for tuning). Decoys: grey_boulder, red_rock, orange_leaf_pile, blue_tarp. Scenario 6 (voice) uses tuning items plus the grey dog and qwen38's own clue wording from the spoken description. Thresholds and rules: DECISIONS 2026-10-11 (patrol-aa, patrol-5d); the e2e pass bars are justified in DECISIONS 2026-10-11 patrol-5d (S4).

## Checks

- [x] offline tests pass
- [x] S1: flight ended at home (area covered)
- [x] S1: grey_dog noticed by the finder (1 of 2 frames in view)
- [x] S1: investigated (1) and alerted with the right clue
- [x] S1: alert within 5 m (error 0.02 m)
- [x] S1: no false alert ([])
- [x] S2: flight ended at home (area covered)
- [x] S2: no alert (got []; decoys investigated 1)
- [x] S2: area covered (100%)
- [x] S3: flight ended at home (area covered)
- [x] S3: no alert (got []; decoys investigated 0)
- [x] S3: area covered (100%)
- [x] S4: flight ended at home (area covered)
- [x] S4: every answer was FALLBACK (123 of 123)
- [x] S4: the sweep finished (100% covered, area covered)
- [x] S4: no alert
- [x] S5: flight ended at home (area covered)
- [ ] S5: every clue found (3/4; missed ['green_sleeping_bag'])
- [x] S5: no duplicate alerts ([])
- [x] S5: no false alert ([])
- [x] S6: heard "Missing hiker, blue backpack, orange tent, gray dog."; qwen38's clue options name ['blue_backpack', 'orange_tent', 'grey_dog'] of ['blue_backpack', 'orange_tent', 'grey_dog'] (['blue_backpack', 'orange_tent', 'gray_dog'])
- [x] S6: every alert read aloud (['A1', 'A2'] of ['A1', 'A2'])
- [x] S6: 'go back to the last alert' heard, routed and executed ([('Go back to the last alert.', 'go_back_to_last_alert', 'CLEF'), ('Stop searching and come home.', 'return_home', 'CLEF')])
- [x] S6: 'stop searching and come home' executed, flight ended at home (operator: return home)
- [x] S6: no false alert ([])

## Metrics

| scenario | recall | false alerts | first find s | loc err m | covered | m² per battery | frames | Clef calls | LLM calls | alerts/candidates | investigations (mean s, decision h) | sweep ms p50/p90 | confirm ms p50/p90 | Clef ms, qwen38 idle | Clef ms, qwen38 busy | qwen38 calls by role | sim s | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 item present | 1/1 | 0 | 148.01 | [0.02] | 100% | 115837 | 97 | 159 (1.64/frame) | 2 | 1/291 | 1 (9.5 s, 20.0 m) | 227/265 | 2026/2026 | 224/243 (n 136) | 284/337 (n 23) | {'note': 1, 'trail': 1} | 397.6 | 46.9 |
| 2 decoys | 0/0 | 0 | None | [] | 100% | 100787 | 103 | 169 (1.64/frame) | 0 | 0/309 | 1 (11.2 s, 20.0 m) | 369/401 | 2656/2656 | 370/401 (n 169) | None/None (n 0) | {} | 457.0 | 74.7 |
| 3 empty | 0/0 | 0 | None | [] | 100% | 107563 | 97 | 164 (1.69/frame) | 0 | 0/291 | 3 (9.5 s, 20.0 m) | 313/320 | 408/408 | 313/321 (n 164) | None/None (n 0) | {} | 429.0 | 62.0 |
| 4 Clef off | 0/1 | 0 | None | [] | 100% | 96154 | 41 | 123 (3.00/frame) | 0 | 0/123 | 0 (None s, None m) | None/None | None/None | None/None (n 123) | None/None (n 0) | {} | 187.6 | 3.0 |
| 5 several | 3/4 | 0 | 125.54 | [0.03, 0.03, 1.7] | 100% | 34929 | 354 | 500 (1.41/frame) | 8 | 3/1062 | 30 (7.0 s, 19.5 m) | 357/402 | 466/543 | 357/374 (n 445) | 436/613 (n 55) | {'note': 3, 'trail': 3, 'second_opinion': 2} | 1317.7 | 219.0 |
| 6 voice | 2/3 | 0 | 89.19 | [0.1, 0.02] | 23% | 58058 | 21 | 39 (1.86/frame) | 4 | 2/63 | 3 (11.0 s, 20.0 m) | 320/347 | 516/516 | 320/347 (n 35) | 1564/1564 (n 4) | {'note': 2, 'trail': 2} | 186.5 | 29.8 |

## Steps

| step | wall s | detail |
|---|---|---|
| offline tests | 1.4 | `70 passed in 1.27s` |
| S1 item present | 47.7 | `search --terrain grass --seed 321 --items grey_dog,grey_boulder --clues grey_dog --out runs/s6-var-300/s1 --think` |
| S2 decoys | 75.6 | `search --terrain snow --seed 322 --items blue_tarp,red_rock,orange_leaf_pile,grey_boulder --clues blue_backpack,red_jacket,orange_tent,grey_dog --out runs/s6-var-300/s2 --think` |
| S3 empty | 62.8 | `search --terrain grass --seed 323 --items  --clues blue_backpack,orange_tent,grey_dog --out runs/s6-var-300/s3 --think` |
| S4 Clef off | 3.9 | `search --terrain snow --seed 324 --items blue_backpack --clues blue_backpack --out runs/s6-var-300/s4 --clef-url http://127.0.0.1:9/v1/systemone --half 50 --think` |
| S5 several | 219.9 | `search --terrain snow --seed 345 --items grey_dog,green_sleeping_bag,yellow_helmet,sos_rocks,grey_boulder,orange_leaf_pile --clues grey_dog,green_sleeping_bag,yellow_helmet,sos_rocks --out runs/s6-var-300/s5 --think` |
| S6 voice | 35.0 | `search --terrain grass --seed 326 --items blue_backpack,orange_tent,grey_dog,blue_tarp --clues blue_backpack,orange_tent,grey_dog --out runs/s6-var-300/s6 --describe-wav fixtures/voice/describe_demo.wav --speak --voice-script {"alert:1": "fixtures/voice/go_back_alert.wav", "alert:2": "fixtures/voice/return_home_search.wav"} --think` |

## Preflight

```
{
 "clef_ok": true,
 "clef_wait_s": 0.0,
 "hold_status": "open: model calls pass; qwen38 (ready) loaded",
 "memory_free": "System-wide memory free percentage: 26%",
 "qwen38": "ok: OK",
 "qwen38_s": 0.4
}
```
