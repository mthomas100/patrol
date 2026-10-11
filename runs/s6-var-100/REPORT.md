# Patrol search e2e: s6-var-100

**Result: FAIL**

Command: `tests/e2e_search.sh --only 1,2,3,4,5,6`; total wall time 493 s. Versions: {"python": "3.12.14", "mujoco": "3.15.0", "clef": "clef-flash-mlx (mlx-community/clef-flash-8bit @ dfa0993, upstream Cloudflare/clef-flash @ 17f0b0a)", "llm": "qwen38 via llama-swap :8090", "git": "78aa27a"}.

Held-out items: grey_dog, green_sleeping_bag, yellow_helmet, sos_rocks (never used for tuning). Decoys: grey_boulder, red_rock, orange_leaf_pile, blue_tarp. Scenario 6 (voice) uses tuning items plus the grey dog and qwen38's own clue wording from the spoken description. Thresholds and rules: DECISIONS 2026-10-11 (patrol-aa, patrol-5d); the e2e pass bars are justified in DECISIONS 2026-10-11 patrol-5d (S4).

## Checks

- [x] offline tests pass
- [x] S1: flight ended at home (area covered)
- [x] S1: grey_dog noticed by the finder (2 of 2 frames in view)
- [x] S1: investigated (1) and alerted with the right clue
- [x] S1: alert within 5 m (error 0.03 m)
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
- [x] S5: flight ended at home (battery 15% leaves only the return reserve)
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
| 1 item present | 1/1 | 0 | 93.84 | [0.03] | 100% | 67016 | 110 | 166 (1.51/frame) | 2 | 1/330 | 1 (10.8 s, 20.0 m) | 243/288 | 2326/2326 | 241/255 (n 143) | 302/399 (n 23) | {'note': 1, 'trail': 1} | 459.1 | 51.8 |
| 2 decoys | 0/0 | 0 | None | [] | 100% | 67725 | 98 | 166 (1.69/frame) | 0 | 0/294 | 2 (9.3 s, 20.0 m) | 390/409 | 1515/538 | 390/411 (n 166) | None/None (n 0) | {} | 454.3 | 75.4 |
| 3 empty | 0/0 | 0 | None | [] | 100% | 68817 | 104 | 163 (1.57/frame) | 0 | 0/312 | 1 (10.4 s, 20.0 m) | 340/354 | 2422/2422 | 340/354 (n 163) | None/None (n 0) | {} | 447.2 | 66.1 |
| 4 Clef off | 0/1 | 0 | None | [] | 100% | 64103 | 41 | 123 (3.00/frame) | 0 | 0/123 | 0 (None s, None m) | None/None | None/None | None/None (n 123) | None/None (n 0) | {} | 187.5 | 3.0 |
| 5 several | 3/4 | 0 | 155.84 | [0.03, 0.0, 0.01] | 89% | 25710 | 280 | 411 (1.47/frame) | 7 | 3/840 | 24 (6.8 s, 19.3 m) | 398/471 | 517/588 | 396/432 (n 349) | 477/674 (n 62) | {'note': 3, 'trail': 3, 'second_opinion': 1} | 1060.8 | 197.1 |
| 6 voice | 2/3 | 0 | 381.06 | [0.01, 0.01] | 100% | 59813 | 109 | 179 (1.64/frame) | 5 | 2/327 | 7 (10.5 s, 17.7 m) | 357/367 | 466/726 | 357/367 (n 171) | 646/919 (n 8) | {'second_opinion': 2, 'note': 2, 'trail': 1} | 514.1 | 87.3 |

## Steps

| step | wall s | detail |
|---|---|---|
| offline tests | 1.4 | `70 passed in 1.24s` |
| S1 item present | 52.7 | `search --terrain grass --seed 121 --items grey_dog,grey_boulder --clues grey_dog --out runs/s6-var-100/s1 --think` |
| S2 decoys | 76.3 | `search --terrain snow --seed 122 --items blue_tarp,red_rock,orange_leaf_pile,grey_boulder --clues blue_backpack,red_jacket,orange_tent,grey_dog --out runs/s6-var-100/s2 --think` |
| S3 empty | 67.0 | `search --terrain grass --seed 123 --items  --clues blue_backpack,orange_tent,grey_dog --out runs/s6-var-100/s3 --think` |
| S4 Clef off | 3.9 | `search --terrain snow --seed 124 --items blue_backpack --clues blue_backpack --out runs/s6-var-100/s4 --clef-url http://127.0.0.1:9/v1/systemone --half 50 --think` |
| S5 several | 198.0 | `search --terrain snow --seed 145 --items grey_dog,green_sleeping_bag,yellow_helmet,sos_rocks,grey_boulder,orange_leaf_pile --clues grey_dog,green_sleeping_bag,yellow_helmet,sos_rocks --out runs/s6-var-100/s5 --think` |
| S6 voice | 92.7 | `search --terrain grass --seed 126 --items blue_backpack,orange_tent,grey_dog,blue_tarp --clues blue_backpack,orange_tent,grey_dog --out runs/s6-var-100/s6 --describe-wav fixtures/voice/describe_demo.wav --speak --voice-script {"alert:1": "fixtures/voice/go_back_alert.wav", "alert:2": "fixtures/voice/return_home_search.wav"} --think` |

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
