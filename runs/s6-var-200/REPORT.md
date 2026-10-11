# Patrol search e2e: s6-var-200

**Result: PASS**

Command: `tests/e2e_search.sh --only 1,2,3,4,5,6`; total wall time 389 s. Versions: {"python": "3.12.14", "mujoco": "3.15.0", "clef": "clef-flash-mlx (mlx-community/clef-flash-8bit @ dfa0993, upstream Cloudflare/clef-flash @ 17f0b0a)", "llm": "qwen38 via llama-swap :8090", "git": "d425744"}.

Held-out items: grey_dog, green_sleeping_bag, yellow_helmet, sos_rocks (never used for tuning). Decoys: grey_boulder, red_rock, orange_leaf_pile, blue_tarp. Scenario 6 (voice) uses tuning items plus the grey dog and qwen38's own clue wording from the spoken description. Thresholds and rules: DECISIONS 2026-10-11 (patrol-aa, patrol-5d); the e2e pass bars are justified in DECISIONS 2026-10-11 patrol-5d (S4).

## Checks

- [x] offline tests pass
- [x] S1: flight ended at home (area covered)
- [x] S1: grey_dog noticed by the finder (2 of 2 frames in view)
- [x] S1: investigated (1) and alerted with the right clue
- [x] S1: alert within 5 m (error 0.02 m)
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

## Metrics

| scenario | recall | false alerts | first find s | loc err m | covered | m² per battery | frames | Clef calls | LLM calls | alerts/candidates | investigations (mean s, decision h) | sweep ms p50/p90 | confirm ms p50/p90 | Clef ms, qwen38 idle | Clef ms, qwen38 busy | qwen38 calls by role | sim s | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 item present | 1/1 | 0 | 218.44 | [0.02] | 100% | 70523 | 107 | 176 (1.64/frame) | 3 | 1/321 | 1 (15.7 s, 12.0 m) | 218/260 | 295/293 | 217/227 (n 153) | 265/358 (n 23) | {'second_opinion': 1, 'note': 1, 'trail': 1} | 436.6 | 48.7 |
| 2 decoys | 0/0 | 0 | None | [] | 100% | 69377 | 99 | 145 (1.46/frame) | 0 | 0/297 | 2 (8.5 s, 20.0 m) | 363/398 | 519/477 | 364/403 (n 145) | None/None (n 0) | {} | 443.6 | 60.5 |
| 3 empty | 0/0 | 0 | None | [] | 100% | 73563 | 98 | 152 (1.55/frame) | 0 | 0/294 | 2 (8.9 s, 20.0 m) | 318/325 | 410/410 | 318/326 (n 152) | None/None (n 0) | {} | 418.5 | 54.9 |
| 4 Clef off | 0/1 | 0 | None | [] | 100% | 64103 | 41 | 123 (3.00/frame) | 0 | 0/123 | 0 (None s, None m) | None/None | None/None | None/None (n 123) | None/None (n 0) | {} | 187.5 | 3.0 |
| 5 several | 4/4 | 0 | 250.83 | [0.02, 0.09, 0.01, 1.7] | 85% | 24569 | 259 | 410 (1.58/frame) | 12 | 4/777 | 34 (7.2 s, 18.8 m) | 362/432 | 473/498 | 360/465 (n 337) | 435/575 (n 73) | {'second_opinion': 4, 'note': 4, 'trail': 4} | 1063.0 | 185.1 |
| 6 voice | 2/3 | 0 | 59.93 | [0.06, 0.04] | 35% | 43556 | 38 | 54 (1.42/frame) | 4 | 2/114 | 3 (8.7 s, 20.0 m) | 318/439 | 499/499 | 315/337 (n 38) | 387/795 (n 16) | {'note': 2, 'trail': 2} | 248.6 | 27.6 |

## Steps

| step | wall s | detail |
|---|---|---|
| offline tests | 1.3 | `70 passed in 1.15s` |
| S1 item present | 49.0 | `search --terrain grass --seed 221 --items grey_dog,grey_boulder --clues grey_dog --out runs/s6-var-200/s1 --think` |
| S2 decoys | 60.8 | `search --terrain snow --seed 222 --items blue_tarp,red_rock,orange_leaf_pile,grey_boulder --clues blue_backpack,red_jacket,orange_tent,grey_dog --out runs/s6-var-200/s2 --think` |
| S3 empty | 55.3 | `search --terrain grass --seed 223 --items  --clues blue_backpack,orange_tent,grey_dog --out runs/s6-var-200/s3 --think` |
| S4 Clef off | 3.3 | `search --terrain snow --seed 224 --items blue_backpack --clues blue_backpack --out runs/s6-var-200/s4 --clef-url http://127.0.0.1:9/v1/systemone --half 50 --think` |
| S5 several | 185.5 | `search --terrain snow --seed 245 --items grey_dog,green_sleeping_bag,yellow_helmet,sos_rocks,grey_boulder,orange_leaf_pile --clues grey_dog,green_sleeping_bag,yellow_helmet,sos_rocks --out runs/s6-var-200/s5 --think` |
| S6 voice | 33.4 | `search --terrain grass --seed 226 --items blue_backpack,orange_tent,grey_dog,blue_tarp --clues blue_backpack,orange_tent,grey_dog --out runs/s6-var-200/s6 --describe-wav fixtures/voice/describe_demo.wav --speak --voice-script {"alert:1": "fixtures/voice/go_back_alert.wav", "alert:2": "fixtures/voice/return_home_search.wav"} --think` |

## Preflight

```
{
 "clef_ok": true,
 "clef_wait_s": 0.0,
 "hold_status": "open: model calls pass; qwen38 (ready) loaded",
 "memory_free": "System-wide memory free percentage: 36%",
 "qwen38": "ok: OK",
 "qwen38_s": 0.4
}
```
