# Patrol search e2e: s6-var-400

**Result: PASS**

Command: `tests/e2e_search.sh --only 1,2,3,4,5,6`; total wall time 485 s. Versions: {"python": "3.12.14", "mujoco": "3.15.0", "clef": "clef-flash-mlx (mlx-community/clef-flash-8bit @ dfa0993, upstream Cloudflare/clef-flash @ 17f0b0a)", "llm": "qwen38 via llama-swap :8090", "git": "35523b0"}.

Held-out items: grey_dog, green_sleeping_bag, yellow_helmet, sos_rocks (never used for tuning). Decoys: grey_boulder, red_rock, orange_leaf_pile, blue_tarp. Scenario 6 (voice) uses tuning items plus the grey dog and qwen38's own clue wording from the spoken description. Thresholds and rules: DECISIONS 2026-10-11 (patrol-aa, patrol-5d); the e2e pass bars are justified in DECISIONS 2026-10-11 patrol-5d (S4).

## Checks

- [x] offline tests pass
- [x] S1: flight ended at home (area covered)
- [x] S1: grey_dog noticed by the finder (2 of 2 frames in view)
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
- [x] S5: every clue found (4/4; missed [])
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
| 1 item present | 1/1 | 0 | 279.64 | [0.02] | 100% | 116895 | 96 | 174 (1.81/frame) | 2 | 1/288 | 1 (11.2 s, 20.0 m) | 229/271 | 2215/2215 | 228/248 (n 152) | 274/320 (n 22) | {'note': 1, 'trail': 1} | 395.3 | 53.2 |
| 2 decoys | 0/0 | 0 | None | [] | 100% | 111790 | 102 | 166 (1.63/frame) | 0 | 0/306 | 1 (8.9 s, 20.0 m) | 361/377 | 1376/1376 | 361/377 (n 166) | None/None (n 0) | {} | 412.4 | 70.1 |
| 3 empty | 0/0 | 0 | None | [] | 100% | 104918 | 100 | 167 (1.67/frame) | 0 | 0/300 | 2 (9.3 s, 20.0 m) | 315/328 | 1320/366 | 315/328 (n 167) | None/None (n 0) | {} | 440.2 | 62.4 |
| 4 Clef off | 0/1 | 0 | None | [] | 100% | 96154 | 41 | 123 (3.00/frame) | 0 | 0/123 | 0 (None s, None m) | None/None | None/None | None/None (n 123) | None/None (n 0) | {} | 187.6 | 3.1 |
| 5 several | 4/4 | 0 | 283.87 | [0.01, 0.03, 0.01, 0.0] | 100% | 36537 | 348 | 504 (1.45/frame) | 9 | 4/1044 | 28 (6.7 s, 19.7 m) | 361/421 | 476/547 | 359/397 (n 428) | 438/562 (n 76) | {'note': 4, 'trail': 4, 'second_opinion': 1} | 1259.7 | 219.2 |
| 6 voice | 2/3 | 0 | 122.78 | [0.05, 0.03] | 80% | 90471 | 84 | 141 (1.68/frame) | 5 | 2/252 | 4 (10.0 s, 18.0 m) | 313/345 | 446/469 | 313/324 (n 127) | 376/615 (n 14) | {'second_opinion': 1, 'note': 2, 'trail': 2} | 405.4 | 61.2 |

## Steps

| step | wall s | detail |
|---|---|---|
| offline tests | 1.4 | `70 passed in 1.25s` |
| S1 item present | 54.0 | `search --terrain grass --seed 421 --items grey_dog,grey_boulder --clues grey_dog --out runs/s6-var-400/s1 --think` |
| S2 decoys | 71.0 | `search --terrain snow --seed 422 --items blue_tarp,red_rock,orange_leaf_pile,grey_boulder --clues blue_backpack,red_jacket,orange_tent,grey_dog --out runs/s6-var-400/s2 --think` |
| S3 empty | 63.3 | `search --terrain grass --seed 423 --items  --clues blue_backpack,orange_tent,grey_dog --out runs/s6-var-400/s3 --think` |
| S4 Clef off | 4.0 | `search --terrain snow --seed 424 --items blue_backpack --clues blue_backpack --out runs/s6-var-400/s4 --clef-url http://127.0.0.1:9/v1/systemone --half 50 --think` |
| S5 several | 220.1 | `search --terrain snow --seed 445 --items grey_dog,green_sleeping_bag,yellow_helmet,sos_rocks,grey_boulder,orange_leaf_pile --clues grey_dog,green_sleeping_bag,yellow_helmet,sos_rocks --out runs/s6-var-400/s5 --think` |
| S6 voice | 70.5 | `search --terrain grass --seed 426 --items blue_backpack,orange_tent,grey_dog,blue_tarp --clues blue_backpack,orange_tent,grey_dog --out runs/s6-var-400/s6 --describe-wav fixtures/voice/describe_demo.wav --speak --voice-script {"alert:1": "fixtures/voice/go_back_alert.wav", "alert:2": "fixtures/voice/return_home_search.wav"} --think` |

## Preflight

```
{
 "clef_ok": true,
 "clef_wait_s": 0.0,
 "hold_status": "open: model calls pass; qwen38 (ready) loaded",
 "memory_free": "System-wide memory free percentage: 16%",
 "qwen38": "ok: OK",
 "qwen38_s": 0.5
}
```
