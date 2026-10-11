# S0 altitude probe

## Sweep: anomaly finder top-3 hit rate (views with the item in frame)

| terrain | item | camera | height m | finder hits | Clef frame clue noul (median) | Clef crop clue noul (median) |
|---|---|---|---|---|---|---|
| snow | blue_backpack | wide | 60 | 0/5 | 0.04 | 0.01 |
| snow | blue_backpack | wide | 40 | 0/5 | 0.04 | 0.01 |
| snow | blue_backpack | wide | 20 | 5/5 | 0.56 | 0.84 |
| snow | blue_backpack | inspect | 60 | 1/5 | 0.06 | 0.01 |
| snow | blue_backpack | inspect | 40 | 5/5 | 0.8 | 0.8 |
| snow | blue_backpack | inspect | 20 | 5/5 | 0.89 | 0.89 |
| snow | blue_tarp | wide | 60 | 5/5 | 0.1 | 0.05 |
| snow | blue_tarp | wide | 40 | 2/5 | 0.06 | 0.01 |
| snow | blue_tarp | wide | 20 | 5/5 | 0.54 | 0.07 |
| snow | blue_tarp | inspect | 60 | 4/5 | 0.15 | 0.07 |
| snow | blue_tarp | inspect | 40 | 5/5 | 0.31 | 0.07 |
| snow | blue_tarp | inspect | 20 | 5/5 | 0.11 | 0.04 |
| grass | blue_backpack | wide | 60 | 0/5 | 0.03 | 0.01 |
| grass | blue_backpack | wide | 40 | 0/5 | 0.04 | 0.01 |
| grass | blue_backpack | wide | 20 | 5/5 | 0.83 | 0.86 |
| grass | blue_backpack | inspect | 60 | 0/5 | 0.06 | 0.01 |
| grass | blue_backpack | inspect | 40 | 5/5 | 0.79 | 0.85 |
| grass | blue_backpack | inspect | 20 | 5/5 | 0.91 | 0.92 |
| grass | blue_tarp | wide | 60 | 5/5 | 0.04 | 0.08 |
| grass | blue_tarp | wide | 40 | 3/5 | 0.04 | 0.1 |
| grass | blue_tarp | wide | 20 | 5/5 | 0.33 | 0.14 |
| grass | blue_tarp | inspect | 60 | 5/5 | 0.16 | 0.11 |
| grass | blue_tarp | inspect | 40 | 5/5 | 0.11 | 0.28 |
| grass | blue_tarp | inspect | 20 | 5/5 | 0.18 | 0.07 |

## Investigate: Clef confirm on the close-up

| terrain | item | height m | clue noul per view | p(clue) per view |
|---|---|---|---|---|
| snow | blue_backpack | 20 | [0.943, 0.906, 0.914, 0.944, 0.943] | [0.935, 0.9, 0.914, 0.931, 0.934] |
| snow | blue_backpack | 12 | [0.957, 0.963, 0.964, 0.961, 0.965] | [0.948, 0.959, 0.951, 0.952, 0.957] |
| snow | blue_tarp | 20 | [0.026, 0.021, 0.036, 0.022, 0.028] | [0.085, 0.101, 0.125, 0.096, 0.094] |
| snow | blue_tarp | 12 | [0.018, 0.026, 0.018, 0.022, 0.028] | [0.095, 0.102, 0.093, 0.091, 0.109] |
| grass | blue_backpack | 20 | [0.958, 0.948, 0.935, 0.96, 0.949] | [0.968, 0.956, 0.942, 0.966, 0.954] |
| grass | blue_backpack | 12 | [0.955, 0.955, 0.962, 0.942, 0.954] | [0.952, 0.957, 0.965, 0.945, 0.955] |
| grass | blue_tarp | 20 | [0.047, 0.045, 0.035, 0.04, 0.04] | [0.171, 0.167, 0.11, 0.156, 0.143] |
| grass | blue_tarp | 12 | [0.041, 0.036, 0.031, 0.031, 0.026] | [0.148, 0.132, 0.12, 0.114, 0.106] |

## Verdict against the rule (DECISIONS 11:50)

- Investigate: range of single thresholds T that separate clue from decoy, per height {20: (0.05, 0.91), 12: (0.04, 0.95)} -> PASS
- Sweep (finder top-3 on >= 4/5 views, both terrains, both items) by camera and height: {'wide 60 m': False, 'wide 40 m': False, 'wide 20 m': True, 'inspect 60 m': False, 'inspect 40 m': True, 'inspect 20 m': True} -> PASS
- **GO**
