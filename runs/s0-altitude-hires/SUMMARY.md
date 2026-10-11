# S0 altitude probe

## Sweep: anomaly finder top-3 hit rate (views with the item in frame)

| terrain | item | camera | height m | finder hits | Clef frame clue noul (median) | Clef crop clue noul (median) |
|---|---|---|---|---|---|---|
| snow | blue_backpack | wide | 60 | 0/5 | - | - |
| snow | blue_backpack | wide | 40 | 0/5 | - | - |
| snow | blue_backpack | wide | 20 | 4/5 | - | - |
| snow | blue_backpack | inspect | 60 | 1/5 | - | - |
| snow | blue_backpack | inspect | 40 | 2/5 | - | - |
| snow | blue_backpack | inspect | 20 | 5/5 | - | - |
| snow | blue_tarp | wide | 60 | 1/5 | - | - |
| snow | blue_tarp | wide | 40 | 5/5 | - | - |
| snow | blue_tarp | wide | 20 | 5/5 | - | - |
| snow | blue_tarp | inspect | 60 | 5/5 | - | - |
| snow | blue_tarp | inspect | 40 | 5/5 | - | - |
| snow | blue_tarp | inspect | 20 | 5/5 | - | - |
| grass | blue_backpack | wide | 60 | 0/5 | - | - |
| grass | blue_backpack | wide | 40 | 0/5 | - | - |
| grass | blue_backpack | wide | 20 | 2/5 | - | - |
| grass | blue_backpack | inspect | 60 | 0/5 | - | - |
| grass | blue_backpack | inspect | 40 | 3/5 | - | - |
| grass | blue_backpack | inspect | 20 | 5/5 | - | - |
| grass | blue_tarp | wide | 60 | 2/5 | - | - |
| grass | blue_tarp | wide | 40 | 5/5 | - | - |
| grass | blue_tarp | wide | 20 | 5/5 | - | - |
| grass | blue_tarp | inspect | 60 | 5/5 | - | - |
| grass | blue_tarp | inspect | 40 | 5/5 | - | - |
| grass | blue_tarp | inspect | 20 | 5/5 | - | - |

## Investigate: Clef confirm on the close-up

| terrain | item | height m | clue noul per view | p(clue) per view |
|---|---|---|---|---|
| snow | blue_backpack | 20 | [] | [None, None, None, None, None] |
| snow | blue_backpack | 12 | [] | [None, None, None, None, None] |
| snow | blue_tarp | 20 | [] | [None, None, None, None, None] |
| snow | blue_tarp | 12 | [] | [None, None, None, None, None] |
| grass | blue_backpack | 20 | [] | [None, None, None, None, None] |
| grass | blue_backpack | 12 | [] | [None, None, None, None, None] |
| grass | blue_tarp | 20 | [] | [None, None, None, None, None] |
| grass | blue_tarp | 12 | [] | [None, None, None, None, None] |

## Verdict against the rule (DECISIONS 11:50)

- Investigate: separating threshold per height {20: None, 12: None} -> FAIL
- Sweep (finder top-3 on >= 4/5 views, both terrains, both items) by camera and height: {'wide 60 m': False, 'wide 40 m': False, 'wide 20 m': False, 'inspect 60 m': False, 'inspect 40 m': False, 'inspect 20 m': True} -> FAIL
- **NO-GO**
