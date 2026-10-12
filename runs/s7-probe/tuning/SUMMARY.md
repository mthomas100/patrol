# S7 probe: tuning (50 images, 142 persons)

## Finder recall on person boxes (a person counts when any candidate box overlaps it)
| view | recall@3 | recall@5 | recall@10 | finder ms per 1280x960 frame (median) |
|---|---|---|---|---|
| native | 123/142 (87%) | 130/142 (92%) | 136/142 (96%) | 54 |
| down | 50/142 (35%) | 66/142 (46%) | 95/142 (67%) | 50 |

## Clef sweep question (clues.sweep_schema with the person clue), flight gate unchanged
| view | crops | person noul median (max) | p(investigate) median | pass the sweep gate |
|---|---|---|---|---|
| native | finder crop on a person: 213 | 0.789 (0.949) | 0.876 | 182/213 (85%) |
| native | centred on a person (control): 142 | 0.798 (0.950) | 0.884 | 123/142 (87%) |
| native | finder crop, background: 2187 | 0.011 (0.882) | 0.158 | 46/2187 (2%) |
| down | finder crop on a person: 42 | 0.721 (0.942) | 0.854 | 37/42 (88%) |
| down | centred on a person (control): 142 | 0.701 (0.940) | 0.852 | 125/142 (88%) |
| down | finder crop, background: 108 | 0.007 (0.872) | 0.121 | 15/108 (14%) |

## Clef confirm question on a native close-up (clues.confirm_schema, t_confirm 0.5)
| close-up of | n | alert (choice person and noul >= bar) | noul median |
|---|---|---|---|
| every person (control) | 142 | 130/142 (92%) | 0.872 |
| finder spots on a person, gate passed | 219 | 209/219 (95%) | 0.898 |
| finder spots on background, gate passed | 61 | 14/61 (23%) | 0.098 |

native: alerts off every person box 7 on 50 images (0.14 per image), of which 6 more than 3 m from any box; persons found end to end (finder top 3, sweep gate, confirm) 108/142 (76%)

down: alerts off every person box 7 on 50 images (0.14 per image), of which 1 more than 3 m from any box; persons found end to end (finder top 3, sweep gate, confirm) 40/142 (28%)

Clef latency median 331 ms, p90 759 ms over 2830 calls; 0 failed calls; wall 30.7 min

## Reading (patrol-real, 2026-10-11, tuning half only; held-out half not run yet)

Command: `.venv/bin/python tools/real_probe.py --split tuning` (log `logs/s7_probe_tuning.log`); finder, gates and
schemas exactly as the flight uses them (`anomaly.candidates`, `clues.sweep_schema`/`confirm_schema` with
`real.PERSON`, `SearchConfig` gate values), nothing tuned.

- **Native resolution works; downscaling does not.** The finder catches 87% of people in its top 3 per 1280x960
  native tile (2 cm/px, like the sim sweep at about 32 m), but only 35% when the whole photo is shrunk to 1280 px
  (6.25 cm/px, like 100 m). A person is about 60 px natively and about 19 px downscaled.
- **Clef separates people from real clutter at sweep scale**: person noul median 0.79 on person crops vs 0.011 on 2187
  native background crops; 2% of background crops pass the unchanged sweep gate. On native close-ups (framed like the
  flight's zoom), 92% of all people confirm at the unchanged bar of 0.5.
- **The "false" alerts are people.** All 14 alerts whose spot does not overlap a person box were checked by eye
  (`false_alerts.jpg`, git-ignored, regenerate with the snippet in LOG 2026-10-11 S7): every close-up shows a person,
  either unannotated (GRO_0003, ZRI_0005, BRS_0002 red jacket, MOB_0001) or a few metres off the annotated box
  (BRS_0006-0011 down view). So on 50 real photos there were **no alerts on background**.
- End to end (finder top 3, sweep gate, confirm) at native resolution: 108/142 people (76%); the misses are mostly
  the finder (19 not in its top 3) and the sweep gate on the person's crop (about 13%).
- Caveats: native tiles overlap, so a spot can be counted on up to four tiles (alert counts are per tile, not per
  place). The close-up is the same 2 cm/px photo upsampled, not a real zoom lens, so confirm numbers are a lower
  bound on a sharper close-up. HERIDAL people are often standing in the open in clear weather.
- Clef latency median 331 ms, p90 759 ms over 2830 calls with another stream sharing Clef (211 ms when alone).
