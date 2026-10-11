# Live vs after landing (S6, the core claim)

The same flights scored two ways. **Live:** the drone's own alerts, made by investigating odd spots with a framed zoom close-up during the flight. **After:** only the sweep-height photos the drone brought home, analysed after landing with the same Clef-Flash: the anomaly finder on every saved frame with twice the live candidate budget (k = 6), the confirm question asked of every crop, an alert when Clef picks a clue with its noul >= 0.5 (the live confirm bar), one alert per clue within 6 m. Both scored against the planted items (5 m). Tool: `tools/after_landing.py` (rows: `rows.jsonl`; per run: `<run>/after/after.json`). 2026-10-11 14:00-14:25.

| flight | clues | live found | live false | after found | after false | only live | only after | battery % | live / after per 100% battery | after Clef calls |
|---|---|---|---|---|---|---|---|---|---|---|
| `runs/s4-e2e-2/s1` | 1 | 1 | 0 | 1 | 0 | - | - | 40.3 | 2.48 / 2.48 | 624 |
| `runs/s4-e2e-2/s5` | 4 | 3 | 0 | 3 | 3 | yellow_helmet | sos_rocks | 88.3 | 3.4 / 3.4 | 1116 |
| `runs/s4-e2e-1/s1` | 1 | 1 | 0 | 1 | 0 | - | - | 38.6 | 2.59 / 2.59 | 624 |
| `runs/s4-e2e-1/s5` | 4 | 3 | 0 | 4 | 4 | - | green_sleeping_bag | 74.1 | 4.05 / 5.4 | 1056 |
| `runs/s5-live-owner` | 3 | 3 | 0 | 3 | 0 | - | - | 56.9 | 5.27 / 5.27 | 750 |
| `runs/s4-tune-snow2-edge` | 3 | 3 | 0 | 2 | 0 | orange_tent | - | 48.9 | 6.13 / 4.09 | 690 |
| **total** | 16 | **14** | **0** | **14** | **7** | | | 347.1 | 4.03 / 4.03 | |

## What it says

- **Recall is the same: 14/16 live, 14/16 after.** Clues per battery are equal because both arms use the same flight. Each arm found two clues the other missed. Live only: the 0.3 m yellow helmet (confirmed by the close-up and qwen38's second opinion) and the orange tent on snow. After only: the SOS rocks and one sleeping bag, which the live sweep gate passed over.
- **Precision is not the same: 0 false alerts live, 7 after.** Every after-landing false alert is on background clutter, none within 10 m of a planted item: six "green sleeping bag" on snow at noul 0.52-0.59 (just over the bar) and one "SOS" at 0.72. A ground team would walk to each one. The live loop's close-up is what removes them: in every flight so far it has raised no false alert.
- **The cost differs too.** After-landing asked Clef 624-1,116 times per flight, against the live loop's 140-330 (about 3-4 times as many). That is affordable after landing, but the drone has no time for it in flight.
- **So the core claim holds for precision and not for recall in this sample:** investigating live gives the same clues with no false alerts, and the clues come while the drone is still out. The after pass finds things the live sweep gate passes over. A hybrid is the obvious next step: re-ask after landing, then send the drone or the team only to the spots the close-up has not cleared. This was not built.
- **Caveats.** Six flights: four held-out e2e flights, a live demo flight and one tuning flight. They are simulator renders, and the after pass ran on the same frames the live flight took (its path included the detours). The live per-battery number counts the battery the investigations used; the after pass gets those frames for free.
