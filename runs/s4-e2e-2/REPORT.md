# Patrol search e2e: s4-e2e-2

**Result: FAIL**

Command: `tests/e2e_search.sh --only 1,2,3,4,5,6 --with-corridor`; total wall time 545 s. Versions: {"python": "3.12.14", "mujoco": "3.15.0", "clef": "clef-flash-mlx (mlx-community/clef-flash-8bit @ dfa0993, upstream Cloudflare/clef-flash @ 17f0b0a)", "llm": "qwen38 via llama-swap :8090", "git": "a9ec8eb"}.

Held-out items: grey_dog, green_sleeping_bag, yellow_helmet, sos_rocks (never used for tuning). Decoys: grey_boulder, red_rock, orange_leaf_pile, blue_tarp. Scenario 6 (voice) uses tuning items plus the grey dog and qwen38's own clue wording from the spoken description. Thresholds and rules: DECISIONS 2026-10-11 (patrol-aa, patrol-5d); the e2e pass bars are justified in DECISIONS 2026-10-11 patrol-5d (S4).

## Checks

- [x] offline tests pass
- [x] S1: flight ended at home (area covered)
- [x] S1: grey_dog noticed by the finder (2 of 2 frames in view)
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
- [ ] S5: every clue found (3/4; missed ['sos_rocks'])
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
| 1 item present | 1/1 | 0 | 212.54 | [0.04] | 100% | 63524 | 104 | 162 (1.56/frame) | 3 | 1/312 | 2 (12.5 s, 16.0 m) | 220/259 | 297/297 | 218/226 (n 141) | 270/350 (n 21) | {'second_opinion': 1, 'note': 1, 'trail': 1} | 484.6 | 45.5 |
| 2 decoys | 0/0 | 0 | None | [] | 100% | 71910 | 98 | 158 (1.61/frame) | 0 | 0/294 | 3 (8.5 s, 20.0 m) | 357/365 | 471/471 | 357/366 (n 158) | None/None (n 0) | {} | 427.2 | 63.7 |
| 3 empty | 0/0 | 0 | None | [] | 100% | 71508 | 97 | 166 (1.71/frame) | 0 | 0/291 | 3 (8.6 s, 20.0 m) | 314/321 | 403/403 | 314/322 (n 166) | None/None (n 0) | {} | 430.4 | 58.8 |
| 4 Clef off | 0/1 | 0 | None | [] | 100% | 64103 | 41 | 123 (3.00/frame) | 0 | 0/123 | 0 (None s, None m) | None/None | None/None | None/None (n 123) | None/None (n 0) | {} | 187.5 | 2.9 |
| 5 several | 3/4 | 0 | 220.42 | [0.03, 0.01, 0.0] | 93% | 26895 | 186 | 326 (1.75/frame) | 7 | 3/558 | 22 (6.6 s, 19.6 m) | 355/427 | 466/568 | 353/373 (n 272) | 442/597 (n 54) | {'note': 3, 'trail': 3, 'second_opinion': 1} | 1060.5 | 139.8 |
| 6 voice | 2/3 | 0 | 36.22 | [0.18, 0.04] | 30% | 45661 | 31 | 55 (1.77/frame) | 4 | 2/93 | 3 (6.8 s, 20.0 m) | 328/433 | 476/476 | 305/343 (n 31) | 375/521 (n 24) | {'note': 2, 'trail': 2} | 205.1 | 26.3 |

## Steps

| step | wall s | detail |
|---|---|---|
| offline tests | 1.3 | `59 passed in 1.15s` |
| S1 item present | 45.8 | `search --terrain grass --seed 21 --items grey_dog,grey_boulder --clues grey_dog --out runs/s4-e2e-2/s1 --think` |
| S2 decoys | 64.0 | `search --terrain snow --seed 22 --items blue_tarp,red_rock,orange_leaf_pile,grey_boulder --clues blue_backpack,red_jacket,orange_tent,grey_dog --out runs/s4-e2e-2/s2 --think` |
| S3 empty | 59.1 | `search --terrain grass --seed 23 --items  --clues blue_backpack,orange_tent,grey_dog --out runs/s4-e2e-2/s3 --think` |
| S4 Clef off | 3.3 | `search --terrain snow --seed 24 --items blue_backpack --clues blue_backpack --out runs/s4-e2e-2/s4 --clef-url http://127.0.0.1:9/v1/systemone --half 50 --think` |
| S5 several | 140.8 | `search --terrain snow --seed 35 --items grey_dog,green_sleeping_bag,yellow_helmet,sos_rocks,grey_boulder,orange_leaf_pile --clues grey_dog,green_sleeping_bag,yellow_helmet,sos_rocks --out runs/s4-e2e-2/s5 --think` |
| S6 voice | 31.9 | `search --terrain grass --seed 26 --items blue_backpack,orange_tent,grey_dog,blue_tarp --clues blue_backpack,orange_tent,grey_dog --out runs/s4-e2e-2/s6 --describe-wav fixtures/voice/describe_demo.wav --speak --voice-script {"alert:1": "fixtures/voice/go_back_alert.wav", "alert:2": "fixtures/voice/return_home_search.wav"} --think` |
| corridor regression (seed 1) | 198.1 | `patrol.e2e --seed 1` |

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
