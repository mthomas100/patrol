# Trail reasoning A/B (grass, seeds [5, 6], realtime)

Same flight with qwen38 reordering sectors after each find (trail) and without (notrail). Times are sim seconds; gap = time from the first find to the second (third) find.

| seed | arm | recall | false | finds s | gap 1-2 | gap 1-3 | mission sim s | battery % | plans applied | qwen38 calls | Clef idle n/p50/p90 | Clef while qwen38 busy n/p50/p90 | run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 5 | trail | 3/3 | 0 | [153.4, 266.37, 303.94] | 113.0 | 150.5 | 565.3 | 47.1 | 3 | {'note': 3, 'trail': 3} | [77, 309, 322] | [52, 375, 477] | `runs/s3-trail-ab-rt/grass5-trail` |
| 5 | notrail | 3/3 | 0 | [171.18, 303.05, 343.16] | 131.9 | 172.0 | 459.5 | 38.2 | 0 | {'note': 3} | [96, 310, 342] | [32, 387, 456] | `runs/s3-trail-ab-rt/grass5-notrail` |
| 6 | trail | 2/3 | 0 | [280.59, 332.04, None] | 51.5 | None | 501.6 | 41.8 | 2 | {'note': 2, 'trail': 2} | [91, 317, 386] | [38, 381, 489] | `runs/s3-trail-ab-rt/grass6-trail` |
| 6 | notrail | 3/3 | 0 | [149.92, 266.47, 335.54] | 116.6 | 185.6 | 445.3 | 37.1 | 0 | {'note': 3} | [95, 310, 321] | [33, 370, 456] | `runs/s3-trail-ab-rt/grass6-notrail` |

Reordering saved 42.0 s on average from the first to the second find (per seed [18.9, 65.1]) and 21.5 s to the third (per seed [21.5]). Positive = faster with reordering.
