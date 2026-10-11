# Trail reasoning A/B (grass, seeds [5, 6], lockstep)

Same flight with qwen38 reordering sectors after each find (trail) and without (notrail). Times are sim seconds; gap = time from the first find to the second (third) find.

| seed | arm | recall | false | finds s | gap 1-2 | gap 1-3 | mission sim s | battery % | plans applied | qwen38 calls | Clef idle n/p50/p90 | Clef while qwen38 busy n/p50/p90 | run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 5 | trail | 3/3 | 0 | [136.0, 229.5, 264.5] | 93.5 | 128.5 | 534.5 | 44.5 | 3 | {'note': 3, 'trail': 3} | [69, 300, 326] | [52, 372, 480] | `runs/s3-trail-ab-lock/grass5-trail` |
| 5 | notrail | 3/3 | 0 | [136.0, 245.0, 285.0] | 109.0 | 149.0 | 400.5 | 33.3 | 0 | {'note': 3} | [87, 317, 324] | [30, 415, 504] | `runs/s3-trail-ab-lock/grass5-notrail` |
| 6 | trail | 3/3 | 0 | [147.5, 238.5, 273.5] | 91.0 | 126.0 | 551.0 | 45.9 | 3 | {'note': 3, 'trail': 3} | [85, 318, 345] | [54, 386, 493] | `runs/s3-trail-ab-lock/grass6-trail` |
| 6 | notrail | 3/3 | 0 | [147.5, 282.0, 331.5] | 134.5 | 184.0 | 441.0 | 36.7 | 0 | {'note': 3} | [86, 314, 325] | [32, 382, 466] | `runs/s3-trail-ab-lock/grass6-notrail` |

Reordering saved 29.5 s on average from the first to the second find (per seed [15.5, 43.5]) and 39.2 s to the third (per seed [20.5, 58.0]). Positive = faster with reordering.
