# Trail reasoning A/B (grass, seeds [5, 6], realtime)

Same flight with qwen38 reordering sectors after each find (trail) and without (notrail). Times are sim seconds; gap = time from the first find to the second (third) find.

| seed | arm | recall | false | finds s | gap 1-2 | gap 1-3 | mission sim s | battery % | plans applied | qwen38 calls | Clef idle n/p50/p90 | Clef while qwen38 busy n/p50/p90 | run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 5 | trail | 3/3 | 0 | [160.43, 282.57, 338.9] | 122.1 | 178.5 | 578.9 | 48.2 | 3 | {'note': 3, 'trail': 3} | [67, 300, 308] | [52, 410, 483] | `runs/s3-trail-ab-rt/grass5-trail` |
| 5 | notrail | 3/3 | 0 | [144.8, 265.74, 307.96] | 120.9 | 163.2 | 432.4 | 36.0 | 0 | {'note': 3} | [91, 312, 328] | [31, 380, 491] | `runs/s3-trail-ab-rt/grass5-notrail` |
| 6 | trail | 2/3 | 0 | [261.79, 315.02, None] | 53.2 | None | 486.1 | 40.5 | 2 | {'note': 2, 'trail': 2} | [88, 312, 323] | [38, 377, 489] | `runs/s3-trail-ab-rt/grass6-trail` |
| 6 | notrail | 3/3 | 0 | [150.14, 298.22, 349.82] | 148.1 | 199.7 | 486.4 | 40.5 | 0 | {'note': 3} | [93, 318, 354] | [34, 388, 477] | `runs/s3-trail-ab-rt/grass6-notrail` |

Reordering saved 46.9 s on average from the first to the second find (per seed [-1.2, 94.9]) and -15.3 s to the third (per seed [-15.3]). Positive = faster with reordering.
