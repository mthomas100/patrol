# Patrol search e2e: s4-e2e-1

**Result: FAIL**

Command: `tests/e2e_search.sh --only 6,1,2,3,4,5`; total wall time 326 s. Versions: {"python": "3.12.14", "mujoco": "3.15.0", "clef": "clef-flash-mlx (mlx-community/clef-flash-8bit @ dfa0993, upstream Cloudflare/clef-flash @ 17f0b0a)", "llm": "qwen38 via llama-swap :8090", "git": "7846ea6"}.

Held-out items: grey_dog, green_sleeping_bag, yellow_helmet, sos_rocks (never used for tuning). Decoys: grey_boulder, red_rock, orange_leaf_pile, blue_tarp. Scenario 6 (voice) uses tuning items plus the grey dog and qwen38's own clue wording from the spoken description. Thresholds and rules: DECISIONS 2026-10-11 (patrol-aa, patrol-5d); the e2e pass bars are justified in DECISIONS 2026-10-11 patrol-5d (S4).

## Checks

- [x] offline tests pass
- [x] S6: heard "Missing hiker, blue backpack, orange tent, gray dog."; qwen38's clue options name ['blue_backpack', 'orange_tent', 'grey_dog'] of ['blue_backpack', 'orange_tent', 'grey_dog'] (['blue_backpack', 'orange_tent', 'gray_dog'])
- [x] S6: every alert read aloud (['A1', 'A2'] of ['A1', 'A2'])
- [x] S6: 'go back to the last alert' heard, routed and executed ([('Go back to the last alert.', 'go_back_to_last_alert', 'CLEF'), ('Stop searching and come home.', 'return_home', 'CLEF')])
- [x] S6: 'stop searching and come home' executed, flight ended at home (operator: return home)
- [x] S6: no false alert ([])
- [x] S1: flight ended at home (area covered)
- [x] S1: grey_dog noticed by the finder (2 of 2 frames in view)
- [x] S1: investigated (1) and alerted with the right clue
- [x] S1: alert within 5 m (error 0.04 m)
- [x] S1: no false alert ([])
- [x] S2: flight ended at home (area covered)
- [x] S2: no alert (got []; decoys investigated 1)
- [x] S2: area covered (100%)
- [x] S3: flight ended at home (area covered)
- [x] S3: no alert (got []; decoys investigated 0)
- [x] S3: area covered (100%)
- [x] S4: flight ended at home (area covered)
- [x] S4: every answer was FALLBACK (91 of 91)
- [x] S4: the sweep finished (100% covered, area covered)
- [x] S4: no alert
- [x] S5: flight ended at home (area covered)
- [ ] S5: every clue found (3/4; missed ['green_sleeping_bag'])
- [x] S5: no duplicate alerts ([])
- [x] S5: no false alert ([])

## Metrics

| scenario | recall | false alerts | first find s | loc err m | covered | m² per battery | frames | Clef calls | LLM calls | alerts/candidates | investigations (mean s, decision h) | sweep ms p50/p90 | confirm ms p50/p90 | Clef ms, qwen38 idle | Clef ms, qwen38 busy | qwen38 calls by role | sim s | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 6 voice | 2/3 | 0 | 36.24 | [0.05, 0.04] | 40% | 49827 | 37 | 61 (1.65/frame) | 4 | 2/111 | 3 (9.1 s, 20.0 m) | 309/442 | 508/508 | 306/319 (n 38) | 349/477 (n 23) | {'note': 2, 'trail': 2} | 249.7 | 29.5 |
| 1 item present | 1/1 | 0 | 196.72 | [0.04] | 100% | 66321 | 104 | 141 (1.36/frame) | 3 | 1/312 | 1 (15.8 s, 12.0 m) | 241/292 | 350/336 | 240/250 (n 122) | 294/392 (n 19) | {'second_opinion': 1, 'note': 1, 'trail': 1} | 464.1 | 46.4 |
| 2 decoys | 0/0 | 0 | None | [] | 100% | 82848 | 96 | 127 (1.32/frame) | 0 | 0/288 | 1 (8.5 s, 20.0 m) | 362/379 | 469/469 | 362/380 (n 127) | None/None (n 0) | {} | 371.3 | 53.2 |
| 3 empty | 0/0 | 0 | None | [] | 100% | 72727 | 96 | 128 (1.33/frame) | 0 | 0/288 | 3 (7.9 s, 20.0 m) | 320/343 | 420/420 | 321/354 (n 128) | None/None (n 0) | {} | 423.3 | 48.1 |
| 4 Clef off | 0/1 | 0 | None | [] | 100% | 64103 | 41 | 91 (2.22/frame) | 0 | 0/123 | 0 (None s, None m) | None/None | None/None | None/None (n 91) | None/None (n 0) | {} | 187.5 | 2.9 |
| 5 several | 3/4 | 0 | 543.34 | [0.08, 0.02, 0.01] | 98% | 33706 | 176 | 269 (1.53/frame) | 10 | 3/528 | 17 (8.0 s, 18.1 m) | 372/446 | 474/557 | 368/455 (n 220) | 434/560 (n 49) | {'second_opinion': 4, 'note': 3, 'trail': 3} | 890.2 | 126.6 |

## Steps

| step | wall s | detail |
|---|---|---|
| offline tests | 1.3 | `59 passed in 1.17s` |
| S6 voice | 41.8 | `search --terrain grass --seed 26 --items blue_backpack,orange_tent,grey_dog,blue_tarp --clues blue_backpack,orange_tent,grey_dog --out runs/s4-e2e-1/s6 --describe-wav fixtures/voice/describe_demo.wav --speak --voice-script {"alert:1": "fixtures/voice/go_back_alert.wav", "alert:2": "fixtures/voice/return_home_search.wav"} --think` |
| S1 item present | 47.3 | `search --terrain grass --seed 21 --items grey_dog,grey_boulder --clues grey_dog --out runs/s4-e2e-1/s1 --think` |
| S2 decoys | 54.1 | `search --terrain snow --seed 22 --items blue_tarp,red_rock,orange_leaf_pile,grey_boulder --clues blue_backpack,red_jacket,orange_tent,grey_dog --out runs/s4-e2e-1/s2 --think` |
| S3 empty | 48.9 | `search --terrain grass --seed 23 --items  --clues blue_backpack,orange_tent,grey_dog --out runs/s4-e2e-1/s3 --think` |
| S4 Clef off | 3.8 | `search --terrain snow --seed 24 --items blue_backpack --clues blue_backpack --out runs/s4-e2e-1/s4 --clef-url http://127.0.0.1:9/v1/systemone --half 50 --think` |
| S5 several | 127.5 | `search --terrain snow --seed 25 --items grey_dog,green_sleeping_bag,yellow_helmet,sos_rocks,grey_boulder,orange_leaf_pile --clues grey_dog,green_sleeping_bag,yellow_helmet,sos_rocks --out runs/s4-e2e-1/s5 --think` |

## Preflight

```
{
 "clef_ok": true,
 "clef_wait_s": 0.0,
 "hold_status": "open: model calls pass; qwen38 (ready) loaded",
 "memory_free": "System-wide memory free percentage: 30%",
 "qwen38": "ok: OK",
 "qwen38_s": 1.2
}
```
