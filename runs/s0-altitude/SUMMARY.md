# S0 altitude probe

## Sweep: anomaly finder top-3 hit rate (views with the item in frame)

| terrain | item | camera | height m | finder hits | Clef frame clue noul (median) | Clef crop clue noul (median) |
|---|---|---|---|---|---|---|
| snow | blue_backpack | wide | 60 | 0/5 | 0.01 | 0.01 |
| snow | blue_backpack | wide | 40 | 0/5 | 0.02 | 0.01 |
| snow | blue_backpack | wide | 20 | 4/5 | 0.05 | 0.55 |
| snow | blue_backpack | inspect | 60 | 1/5 | 0.02 | 0.01 |
| snow | blue_backpack | inspect | 40 | 2/5 | 0.07 | 0.01 |
| snow | blue_backpack | inspect | 20 | 5/5 | 0.77 | 0.79 |
| snow | blue_tarp | wide | 60 | 1/5 | 0.08 | 0.01 |
| snow | blue_tarp | wide | 40 | 5/5 | 0.08 | 0.04 |
| snow | blue_tarp | wide | 20 | 5/5 | 0.12 | 0.05 |
| snow | blue_tarp | inspect | 60 | 5/5 | 0.21 | 0.05 |
| snow | blue_tarp | inspect | 40 | 5/5 | 0.1 | 0.06 |
| snow | blue_tarp | inspect | 20 | 5/5 | 0.27 | 0.08 |
| grass | blue_backpack | wide | 60 | 0/5 | 0.01 | 0.01 |
| grass | blue_backpack | wide | 40 | 0/5 | 0.02 | 0.01 |
| grass | blue_backpack | wide | 20 | 1/5 | 0.6 | 0.01 |
| grass | blue_backpack | inspect | 60 | 0/5 | 0.02 | 0.01 |
| grass | blue_backpack | inspect | 40 | 3/5 | 0.09 | 0.41 |
| grass | blue_backpack | inspect | 20 | 5/5 | 0.82 | 0.87 |
| grass | blue_tarp | wide | 60 | 5/5 | 0.03 | 0.12 |
| grass | blue_tarp | wide | 40 | 5/5 | 0.03 | 0.1 |
| grass | blue_tarp | wide | 20 | 5/5 | 0.07 | 0.06 |
| grass | blue_tarp | inspect | 60 | 5/5 | 0.1 | 0.17 |
| grass | blue_tarp | inspect | 40 | 5/5 | 0.1 | 0.09 |
| grass | blue_tarp | inspect | 20 | 5/5 | 0.07 | 0.09 |

## Investigate: Clef confirm on the close-up

| terrain | item | height m | clue noul per view | p(clue) per view |
|---|---|---|---|---|
| snow | blue_backpack | 20 | [0.934, 0.448, 0.87, 0.923, 0.919] | [0.921, 0.617, 0.872, 0.913, 0.904] |
| snow | blue_backpack | 12 | [0.936, 0.946, 0.952, 0.95, 0.944] | [0.922, 0.932, 0.936, 0.933, 0.931] |
| snow | blue_tarp | 20 | [0.031, 0.021, 0.056, 0.022, 0.023] | [0.102, 0.094, 0.18, 0.105, 0.089] |
| snow | blue_tarp | 12 | [0.021, 0.026, 0.019, 0.022, 0.03] | [0.087, 0.11, 0.092, 0.102, 0.125] |
| grass | blue_backpack | 20 | [0.698, 0.922, 0.258, 0.845, 0.884] | [0.82, 0.919, 0.529, 0.888, 0.919] |
| grass | blue_backpack | 12 | [0.913, 0.931, 0.937, 0.919, 0.878] | [0.911, 0.935, 0.945, 0.927, 0.898] |
| grass | blue_tarp | 20 | [0.048, 0.042, 0.051, 0.027, 0.03] | [0.177, 0.15, 0.176, 0.111, 0.139] |
| grass | blue_tarp | 12 | [0.036, 0.104, 0.045, 0.03, 0.024] | [0.129, 0.242, 0.154, 0.108, 0.11] |

## Verdict against the rule (DECISIONS 11:50)

- Investigate: separating threshold per height {20: 0.05, 12: 0.05} -> PASS
- Sweep (finder top-3 on >= 4/5 views, both terrains, both items) by camera and height: {'wide 60 m': False, 'wide 40 m': False, 'wide 20 m': False, 'inspect 60 m': False, 'inspect 40 m': False, 'inspect 20 m': True} -> FAIL
- **GO at a lower sweep height only**
