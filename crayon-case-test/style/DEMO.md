# Crayon Case — our demo

One example among many. Don't reuse its story, arc, shots, props or timings.

Demo: *Alder Street* (29 s, fictional case) · `test.mp4` · source in [`demo/`](demo/). Music and foley only: no voice, no subtitles (the channel burns subtitles in afterwards).

## Story & structure

One page records the night someone stopped being there. The date is written in crayon; a house draws itself; a woman is drawn in the side window, then rubbed out, leaving a grey ghost; her window is coloured over in faded blue. A stain spreads across the lawn and reveals clear-wax footprints from the door to the open gate, where a glove is drawn and coloured hot pink. The boil calms almost to still and three music-box notes end on an unresolved step.

Nothing violent is drawn: an erased person, a recoloured window, footprints and one object carry it.

| Time | Beat | Native move |
|---|---|---|
| 0–4.2 | "ALDER STREET" / "NOV. 14, 1987" written letter by letter | child logic (the date on the page) |
| 4.2–8.9 | ground, tree, house, fence drawn slowly; walls coloured | drawn live |
| 8.9–11.2 | a woman drawn in the window, blank face | — |
| 11.2–14.4 | rubbed out in back-and-forth passes; a ghost stays | **rubbed out** |
| 14.4–15.8 | window coloured faded blue, behind her ghost | colouring is an action |
| 15.8–22.8 | the stain spreads, footprints appear | **clear-wax resist** |
| 22.8–26 | the glove drawn and coloured hot pink | colouring is an action; the one accent |
| 26–29 | boil calms to ~0.3 | boil |

## Shots

One continuous camera over one page (world 2400×1350; full page = scale 0.8).

| Beat | Camera |
|---|---|
| Date | Locked close on the title corner (scale 1.45) |
| House | Slow move down and across to the house (4.4 s) |
| Window | Slow push toward the window (scale 1.38), locked through the erasing and the recolouring |
| Stain | Pull out to a held wide (scale 0.86): the stain is the motion |
| Clue | Push toward the gate (scale 1.62), creeping in to 1.68 on the hold |

## Score structure

A slow music box in A minor (comb-tine synthesis, partials 1 / 2.76 / 5.40 / 8.9, a detuned second tine): the theme's first phrase, then it starts again and **winds down** (each note flatter and later: ×0.995, ×0.985, ×0.965), a spring rattle, and a hard stop at 13.9 s mid-phrase. One full beat of silence (only the clock). A low drone (A1 + A2 + a little E2, slow beating, filtered air) enters at 5 s, drops out in the silence, swells under the stain. One felt-muted low A under the pink. The end: three broken music-box notes, E5 – C5 – B4, never resolving to A.

Foley: crayon = band-passed noise × stick-slip grain, shaped into strokes (writing fast and bright; lines slow; colouring at ~5.5 swishes/s; the pink heavy, with a low-mid body); eraser = 220–1400 Hz friction at 4.3 bursts/s plus chatter, then crumbs brushed off; stain = low brown-noise swell + fine wet crackle + a few tiny drips; room tone, faint wind, a clock every second (louder in the silence). Music sits ~1–2 dB under the foley.

## Palette & props

- Paper `#dccca8`, aged (uAge 1): uneven yellowing, 4 tide-ring stains in page coordinates, foxing, one fold crease at page x 1545, browned edges (edge 0.85), vignette 0.42.
- Box: indigo line `#2d3263`, grey-brown walls `#8a7d6b`, umber roof `#5a4636`, wood `#4e4037`, olive-grey grass `#77755c` / leaves `#6a6a55`, faded blue `#7d8c9b` (the recoloured window), coat `#5f7186`, ash skin `#c9bba3` (also the lit window), ink-grey hair `#3b3936`, path `#b3a68b`, clear wax, hot pink `#FF1493` (the glove only).
- The stain: transmission `(0.62, 0.52, 0.36)`, resist 0.95 between coverage 0.78 and 0.97 (so only the extra clear wax resists, not the grass hatching), edge 2.0.
- Boil amplitude 0.5 throughout, falling to 0.15 at 25.6–27.5 s. Lines draw in 1.2–2.4 s.
- Props: house (gable + slanted side wall), round tree, path, picket fence with an open gate, 11 clear-wax footprints, the woman (bust), the glove.

## Build notes

```
demo/
  gl.js      WebGL2 compositor: aged paper (setAge: stains, foxing, crease), wax adhesion, knock-out,
             crayon({ghost}) for erased drawings, crayon({clear}) for clear wax, wash({r0, r1}) resist window, edge browning
  crayon.js  stroke engine (from crayon-book, unchanged)     rig.js  parts, occlusion, tubes (unchanged)
  looks.js   the crayon boxes (base and case)                frame.js  style frame (?test=frame&look=base|case), person(), bust()
  film.js    timeline, camera, eraser mask, stain growth, events      audio.py  score + foley + mix
  build.sh   events → audio → render → mux → poster
```

1. `node core/render/still.mjs <demo> 0.5 --q 'test=frame&look=case'` — the style frame; `look=base` for the comparison.
2. `node core/render/still.mjs <demo> 1.5 4 6.5 9.5 10.9 12.8 15.2 19 22.7 25.5 28.5` + `sheet.py` — review.
3. `node core/render/events.mjs <demo>` → `audio.py` (set `STEMS=1` to write stems and check levels per second).
4. `node core/render/video.mjs <demo> --fps 24 --workers 4` → `mux.sh … 24 0` (no grain: the paper is the grain).

**Erasing**: draw the figure into its own group, draw the eraser path into a mask canvas (thick round strokes, back and forth, top to bottom), split the group into *alive* (`destination-out` mask) and *ghost* (`destination-in` mask), composite alive normally and ghost with `crayon({ghost: 1})`. Crumbs: small grey dabs near the eraser head at 24 fps.

Pitfalls met in this demo:

- **Paper-coloured wax still showed on the grass** (it covers the hatching) → clear wax adds coverage only (`crayon({clear: true})`: blend ZERO/ONE for colour).
- **The stain didn't show on the grass**: the grass wax resisted it as much as the footprints → raise the resist window to coverage 0.78–0.97.
- **The woman's hair outline at eye level read as glasses** → hair outer edge ends well above the eyes.
- **Stains drifted** before the paper camera was set → `paperCam(CAM.x·0.8, CAM.y·0.8, CAM.s/0.8)` every frame, stains in page coordinates.
