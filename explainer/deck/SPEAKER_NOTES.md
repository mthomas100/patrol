# Patrol deck: speaker notes (presenter only)

Every number below is on the explainer page. Everything is a simulator result.

## 1. Patrol
- Say: a drone that searches from a spoken description, on one laptop, with no internet.
- Land: 3 of 3 found on a real-time flight, no false alerts; 0.32 s to judge one odd spot.
- Caveat: the map is a simulated flight, not a hillside.

## 2. Everything it sees, thinks and finds
- Say: this is the console at the moment of an alert; one screen shows what the drone sees, what each model thinks and what it found.
- Point at: 1 the header (state, 43% searched, who decided), 3 the camera (the close-up and CONFIRM), 4 the decision trace (Clef-Flash's bars), 8 the alert card (sweep crop beside the close-up, qwen38's note).
- Land: clue chips (2) show qwen38's from-above wording; the chase view (6) is for the audience only, no model sees it.
- Caveat: a replay of the demo flight at 16x speed, captured mid-flight.

## 3. Watch the whole flight
- Say: press play; 3 min 23 s at 3.5x with the alerts read aloud.
- Land: three finds, the tarp checked and dismissed, no false alerts.
- Caveat: this is the stage fallback recording; the operator's spoken commands are not in the audio and qwen38's notes arrive about 10 s after their alerts.

## 4. Searchers start with words, not photos
- Say: the family describes the person's things; nobody has a trained detector for this backpack.
- Land: from 40 m the backpack is about 22 pixels. An alert is about 270 bytes plus a 20 KB photo, so it fits a radio link.
- Caveat: the radio is not built; alerts go to the console.

## 5. A flight in five moments
- Say: speak it, sweep at 40 m, follow a lead down to 20 m, alert, then think ahead.
- Land: backpack confirmed at 94.5%; tent alert 0.24 m from the tent; trail plans found the second item 29.5 s sooner on average.
- Caveat: the 29.5 s comes from a controlled test on two seeds, at 25 to 34% more flying.

## 6. A decoy dismissed, a backpack confirmed
- Say: the blue tarp looks like a backpack from 40 m (17%); the close-up settles it (4%, dismissed). The real backpack goes 61% to 94.5%.
- Land: a confirm needs the right clue named and at least 50% on that clue.
- Caveat: the backpack is a tuning item, so this is the best case, not a held-out result.

## 7. Four models fly it, three built the props
- Say: Clef-Flash is the fast eyes, qwen38 the slow thinker, Parakeet the ears, Kokoro the voice. Code flies and owns safety.
- Land: m3d chained Z-Image Turbo, Apple Vision and Hunyuan3D; about 5 minutes per prop, 8 props.
- Caveat: prop models were used before the flight, not during it.

## 8. Fast loop, slow thinker, code in charge
- Say: Clef-Flash decides per photo in about 0.3 s; qwen38 does a few background jobs in 2 to 5 s each.
- Land: every answer passes through code; no model can steer, override a limit or alert on a fallback. Safety limits: height 8 to 70 m, a 25 m boundary, 10% battery kept for the trip home.
- Caveat: only a second opinion makes the drone wait. The diagram's rows run top to bottom: before take-off, the fast loop, the slow loop.

## 9. Fly high, look close
- Say: the same backpack from 60, 40 and 20 m, then the two closer-look heights.
- Land: the finder found it in 1 of 10 views from 60 m and 10 of 10 from 40 m, so 40 m is the sweep height. 7 lanes at 40 m versus 13 at 20 m.
- Caveat: the smallest clue sets the height (a 0.3 m helmet drops the sweep to 21.8 m).

## 10. Higher means fewer lanes
- Say: at 40 m each photo covers 32.6 m of ground with 22.9 m between lanes; higher is the battery lever.
- Land: up high only notice that a spot looks odd; close up, decide what it is (20 m first, 12 m only if unsure).
- Caveat: the hero numbers are from a 20-minute simulated battery; it is now 30.

## 11. Each model sees only what it must
- Say: cheap work on everything, expensive work on almost nothing.
- Land: one flight: 375 odd spots boxed, 163 crops judged by Clef-Flash, 6 qwen38 jobs.
- Caveat: the chart is a log scale.

## 12. Talking to it
- Say: speech picks from a fixed list of commands; code still flies.
- Land: Parakeet 20 to 90 ms; a command runs only at 45% confidence or more; the spoken description was routed at 94.7%.
- Caveat: the "what have you found" answer is basic so far.

## 13. One laptop, no internet
- Say: an M5 Max with 128 GB runs all four models, the simulator and the console together.
- Land: qwen38 is about 70 GB of the memory; Clef-Flash 0.3 to 0.4 s when the GPU is free, 2 to 6 s when shared.
- Caveat: offline is by design, not yet by test. The Wi-Fi-off rehearsal has not been run.

## 14. It works end to end, in a simulator
- Say: four numbers, all from recorded runs.
- Land: 3 of 3 real-time; 17 of 18 scenario flights; 0 false alerts in 45 flights (95 alerts); live 0 versus 7 false alerts after landing.
- Caveat: small samples. Both methods found 14 of 16 clues; live's advantage is precision, not recall.

## 15. What doesn't work yet
- Say: five honest faults.
- Land: on 20 minutes the four-clue flight ran out of battery; on a realistic 30 it covers everything and 17 of 18 pass. The one miss is the finder never boxing a sleeping bag. Held-out close-ups score only 0.12 to 0.29 (qwen38 rescues them).
- Caveat: why 30 minutes: drones in service fly 40 to 45 min and lose a quarter to a third in the cold. The power-line regression failed once on its known vegetation false alarms.
- Caveat: location accuracy is a best case (flat ground, no GPS error).

## 16. What's next
- Say: from a convincing simulator to evidence on real ground.
- Land: first, the finder's blind spot and the Wi-Fi-off rehearsal (about ten minutes).
- Caveat: real aerial imagery (HERIDAL, SARD, WiSARD) is approved, but dataset licences are still being checked.

