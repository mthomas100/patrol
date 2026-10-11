# Trail reasoning A/B (grass, seeds [5, 6], lockstep)

Same flight with qwen38 reordering sectors after each find (trail) and without (notrail). Times are sim seconds; gap = time from the first find to the second (third) find.

| seed | arm | recall | false | finds s | gap 1-2 | gap 1-3 | mission sim s | battery % | plans applied | qwen38 calls | Clef idle n/p50/p90 | Clef while qwen38 busy n/p50/p90 | run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 5 | trail | 3/3 | 0 | [136.0, 227.5, 282.0] | 91.5 | 146.0 | 532.0 | 44.3 | 3 | {'note': 3, 'trail': 3} | [66, 313, 322] | [53, 378, 486] | `runs/s3-trail-ab-lock/grass5-trail` |
| 5 | notrail | 3/3 | 0 | [136.0, 245.0, 285.0] | 109.0 | 149.0 | 400.5 | 33.3 | 0 | {'note': 3} | [84, 312, 321] | [30, 379, 506] | `runs/s3-trail-ab-lock/grass5-notrail` |
| 6 | trail | 3/3 | 0 | [147.5, 250.5, 285.5] | 103.0 | 138.0 | 559.0 | 46.5 | 3 | {'note': 3, 'trail': 3} | [82, 313, 332] | [57, 375, 491] | `runs/s3-trail-ab-lock/grass6-trail` |
| 6 | notrail | 2/3 | 0 | [147.5, 315.5, None] | 168.0 | None | 425.0 | 35.4 | 0 | {'note': 2} | [103, 314, 324] | [20, 380, 525] | `runs/s3-trail-ab-lock/grass6-notrail` |

Reordering saved 41.2 s on average from the first to the second find (per seed [17.5, 65.0]) and 3.0 s to the third (per seed [3.0]). Positive = faster with reordering.
