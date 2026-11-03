# Crayon Case 蜡笔案卷 — Style Prompt

Based on Crayon Picture Book (crayon-book) from Lemo-Opuscar.

> A child's picture-book page drawn live in wax crayon, on paper that has been in a drawer for thirty years: yellowed, stained, folded. Something on the page is wrong, and it is the only thing in colour.
> References (grammar only): Raymond Briggs' *The Snowman* (1982) (hand-textured frames that breathe, wordless passages, still backgrounds with living figures). Copy none of its characters, song or imagery, and never name it in the film.

## 1. Essence, and what it is not

A children's picture-book page **being drawn while you watch**: wax crayon on old, yellowed paper, a small box of drab crayons, child-logic perspective, colour that spills past the outline, and every line gently **boiling** because each frame is a fresh drawing. The tone is **"a children's picture book where something is wrong"**: quiet, slow, unsentimental, for true-crime documentary. Any topic becomes **one page of a picture book that gets finished, or rubbed out**: drawing, colouring and erasing are the plot. In a world of grey-brown, ink grey and faded blue, **one hot-pink crayon** marks what matters.

It is not "cute vector art with a crayon filter": the look comes from **material physics** (wax sticks only to the peaks of the paper tooth, pressure decides how much of the tooth it reaches, a wash is repelled by wax, an eraser never takes it all). Not a whiteboard explainer (no marker, no hand), not a watercolour painting (the stain is a guest, the crayon the host), not a chalkboard. Not horror: no gore, no jump scares, no blood. The unease comes from the gap between the child's medium and what it records.

## 2. Materials & rendering

- **Paper: old and handled.** Yellowed off-white (around `#dccca8`), unevenly toned in big soft patches; **2–4 dried tide-ring stains** (water, tea) with darker rims; small rust **foxing** spots; **one fold crease**; edges browned and slightly ragged. Stains, foxing and crease are **anchored to the page** (they pan and zoom with it, like the tooth), never screen-fixed. The tooth is anchored to the page (it pans with the camera; on zoom two octaves cross-fade so grains stay ~1 px on screen): three octaves of value noise plus a horizontal fibre term. A final pass embosses it (lit top-left), less where wax filled the tooth. Stronger vignette than the base, browner at the corners.
- **Wax adhesion (the core rule)**: every crayon layer is a canvas where RGB = colour and **A = pressure**; the shader deposits wax where `tooth > 1 − k·pressure` (soft edge). Light pressure = speckled peaks; heavy = almost solid, slightly darker.
- **Strokes**: ribbons with a low-frequency hand wobble (1–2 px), width ±15 %, tapered ends, a denser core and 1–2 thin streaks. Characters and buildings get the heaviest outline; refined "adult" objects about half.
- **Colouring**: back-and-forth zig-zag hatching with a visible gap, each pass at a slightly different pressure; **overshoot the outline by a few px**; a lighter cross-hatch pass on big areas.
- **Erasing (new)**: crayon never fully erases. An erased drawing becomes a **ghost**: the wax smears sideways along the eraser's strokes, loses about half its body and turns grey; outlines survive as faint dents. The eraser travels in short back-and-forth passes, like the hatching. Use it for the missing, the dead, the lied-about, the thing that was there before.
- **The stain (the wash)**: a separate density canvas multiplied over the page, in **dirty water / tea brown**. Pigment pools at edges into a tide ring (density minus blurred density), granulates in the deepest pits, blooms with noise, and is **resisted by wax** (density × (1 − ~0.9·wax coverage)). It spreads slowly, as a spill does, not as a brush stroke.
- **Occlusion**: a front part erases what is behind it inside its outline; characters "keep the paper bare" behind them (a knock-out that restores the aged paper and resets wax), the way a child draws the figure first and colours around it.
- **Characters**: a skilled adult imitating a child, **plain and quiet**: round head (≈2.5 heads tall), **two small dot eyes with no catchlight, no mouth (or a short flat line), no cheeks**, tube limbs, mitten hands, simple hair masses, plain coats. No smiles, no tears, no drawn emotion: posture and distance carry it. Victims are never drawn cute or comic. **Child perspective**: gable front + slanted side wall; people bigger than doors.

## 3. Colour logic

- **A small box of drab crayons, about seven, never more**: grey-brown, umber, ink grey (먹색), faded blue, olive-grey, ash (skin), plus clear wax for resist. Outlines in one dark colour (indigo, dark brown, plum), **never black**; indigo `#2d3263` by default.
- **One accent: hot pink `#FF1493`, and only it.** Only on what matters to the case: an important object, anything tied to the perpetrator, a key clue, **and blood**. Always at full pressure, so it reads solid. Never on a victim's face, never decoration, never a second accent colour. If a frame has nothing that matters, it has no pink.
- **Blood is always hot pink, never red or brown.** On yellowed paper a brown or dark-red stain can't be read as anything. Draw blood as evidence, not violence: a small pool or stain, drops, smears, footprints or a trail leading somewhere, an object marked with it. A pool or stain is a wash in **cover mode** (`wash({ color: [1, 0.078, 0.576], cover: 1 })`): the pigment covers the paper instead of filtering it, so it stays hot pink on yellowed paper. Footprints, drops and smears are drawn in pink crayon. Never splatter, wounds or blood on a body.
- **At most one wash per film**: either the **stain** (dirty water / tea brown, transmission around `(0.62, 0.52, 0.36)`: time, neglect, a spill that reveals clear wax) or **blood** (hot pink, cover mode, above). It never paints the characters.
- Lots of bare (yellowed) paper; value comes from pressure, not extra hues. Pressure on big areas can stay a little lower than the base, so the paper shows through and the page reads faded.
- Example box: *Alder Street* — indigo line, grey-brown walls `#8a7d6b`, umber roof `#5a4636`, wood `#4e4037`, olive-grey grass `#77755c`, faded blue `#7d8c9b` / coat `#5f7186`, ash skin `#c9bba3`, ink-grey hair `#3b3936`, clear wax, hot pink `#FF1493`.

## 4. Type & subtitles

- **Subtitles are not drawn on the page.** They are burned in afterwards, the same in every style of the channel: bottom-centre, **white, Freesentation 4 Regular** (OFL, supplied by the user), with a soft dark shadow and a thin dark edge so white reads on yellowed paper (never a dark box). Keep the bottom ~14 % of the frame free of key action and of pink. Films are rendered without subtitles; the `.srt` is delivered alongside.
- **Titles** (place, date, names, chapter cards) are written **on the page in crayon** in **Freesentation 6 SemiBold**, in the outline colour, slightly tracked, each glyph tilted and offset, boiling on twos, written letter by letter. You can't fade crayon: a title leaves by the camera moving off it, a page turn, being coloured over, or **being erased (leaving its ghost)**.

## 5. Motion quality

- **Everything drawn steps at 12 fps** (lines, colouring, erasing, characters, boil seed); camera, the stain's spreading edge and the eraser crumbs run at 24 fps.
- **Slow.** Lines reveal along their length in **1.2–2.5 s** (base: 0.4–0.9 s); colouring row by row, unhurried; long holds. Prefer one thing being drawn or erased at a time.
- **Boil**: each stroke re-jitters offset (<1 px), wobble and hatching rows every 2 frames, **at about half the base amplitude** throughout; characters full, background lines ~0.6, background colouring still. Calm it further, nearly still, at the heaviest moments.
- **Drawing on and rubbing out** are the main motions. Erasing takes as long as drawing; the ghost stays.
- **Acting**: substitution, a new drawing per pose; few poses, held long. A child's drawing doesn't in-between. Figures mostly stand, look, wait.
- **Colouring is an action**: being coloured in *is* doing (a coat scribbled on = putting it on; a window filled with faded blue = nobody home; a pink object coloured in = this matters now).

## 6. Camera grammar

The camera moves over a large page. A vocabulary, not a route; every move needs a reason. Opening and ending come from the topic. Moves are slower than the base.

| Move | What it expresses | Can serve |
|---|---|---|
| Locked full page | Paper before drawing; the whole picture | a beginning from nothing; a tableau; a reveal that needs the page |
| Push toward a character | "This one" | a title giving way; a person who matters |
| Locked medium close-up | Substitution poses act | a decision; a lie; a silence |
| Tilt along a gaze | We see what they see | discovery; dread; something huge |
| Tight follow | The world draws itself ahead of the subject | a route; a timeline; a search |
| Held wide while the stain spreads | The material is the motion | a reveal; time passing; evidence surfacing |
| Slow truck across the page | Reading left to right | a list; a sequence; a family; suspects |
| Pull out past the page edge | The page is an object | a page in a case file, a drawer, an evidence bag |
| Page turn | New chapter, time jump | before/after; the next year |

Key figures ≥ 1/4 of frame height in close shots; keep the bottom of the frame quiet for the subtitles. Transitions: drawing on, erasing, colouring over, the stain, a pan or a page turn; never a dissolve.

## 7. Sound palette

- **Slow and low, no bright nursery instruments**: a **slow music box** (lead; it can wind down with a pitch droop, and stop mid-phrase), a **low drone** (bowed or synthesized, sub-heavy, barely moving), sparse low piano or celesta single notes, a soft felt-muted pulse at most. No ukulele, no toy-piano jollity, no shaker, no strings section, no grand-piano melody. One short theme, heard broken most of the film and whole at most once.
- **Silence is a beat**: a full beat of nothing after a reveal; the music box stopping is an event.
- **Foley follows the material**: **crayon** = stick-slip band-passed noise whose grain follows stroke speed, close and dry, often the loudest thing; **eraser** = rubbery low-mid friction in short back-and-forth bursts, crumbs brushed off; the stain = a slow wet creep (soft low-passed noise); a page turn (lift / whoosh / flap); paper handling. Ambience: room tone, a distant clock, wind; no birdsong.
- **Mix**: music low under narration, rising only in wordless passages. **Foley stays well under the voice**: under narration, crayon / eraser / stain sounds sit about 12 dB below the voice (in the first narrated test they were level with it and too loud); in wordless passages they may come up to about 6 dB below where the voice would be. −14 LUFS.
- **Voice**: calm, even, documentary; short lines with breaths. Compress before EQ, cut the highs, de-ess, a small dry room; a few dB over the bed, never louder. Whisper-check every line, dry and on the final mix. One voice across the channel: **Kokoro `bm_george`** (chosen after the narration test; speed around 0.9).

## 8. Native moves

A menu: use the ones your story needs.

- **Clear-wax resist.** Clear (paper-coloured) wax is invisible until the stain passes; hide the evidence in plain sight from the first frame. *Fits content like:* footprints on a lawn; a name in a ledger; a mark under the floorboards.
- **Rubbed out (new).** Erase a figure or an object and leave its ghost: the smear stays for the rest of the scene. *Fits content like:* a person who went missing; an alibi that collapsed; a house that was demolished.
- **Drawn live.** The world draws itself just ahead of the subject. *Fits content like:* a route on the night; a timeline of calls; a family tree.
- **Colouring is an action.** *Fits content like:* a window coloured faded blue = the lights went out; a coat coloured on = leaving the house; the one pink object coloured in = this is the clue.
- **Boil.** A held frame is alive; calming it nearly to still is the film holding its breath. *Fits content like:* a verdict; a long silence; a body never found.
- **Child logic.** Wrong perspective, people bigger than doors, numbers written in the sky. *Fits content like:* a date and time written over the house; a distance written along a road; a count of days.
- **It is a book.** Pull back to the object; turn the page. *Fits content like:* the page as an exhibit in a case file; the next chapter; years later.

## 9. Pitfalls of the medium

- Gaps between stain bands leave clean stripes → overlap blobs and spread from one centre.
- Wavy stain edges and wide light streaks read as hills → small high-frequency waviness, thin faint streaks (α ≤ 0.12).
- Light-pressure colouring goes muddy under a stain → pressure ≥ 0.8 or cross-hatch wherever the stain crosses.
- **White wax shows on yellowed paper** → resist wax is paper-coloured (clear candle wax), not white.
- Text where the stain passes survives it (wax resists) → place it elsewhere or accept it.
- Characters vanish under a stain → composite them *after* the stain.
- Outlines over hair read as a headband, or as frowning brows on a blank face → outline hair masses on their outer edge only; keep the fringe well above the eyes.
- **Dot eyes drawn as hatched blobs look slanted and angry** → small round dabs (gap ≈ 2.5, width ≈ 4), no catchlight.
- **A dark window hides an erased figure** → put ghosts against a mid-value (faded blue, grey-brown), never against ink grey.
- **Paper stains drift on screen** if the paper camera isn't set → always set the paper camera to the page camera (stains are in page coordinates).
- **Pink spreading**: a second pink thing in the frame halves the first → audit every frame for exactly the pink that matters; no pink in the subtitle zone.
- **Blood drawn brown or dark red on yellowed paper reads as dirt** → blood is always hot pink, in cover mode for pools.
- **A blood pool swallows a pink object** in it → keep the pool small and away from the clue; let footprints or a trail lead from one to the other.
- **A multiply wash in hot pink turns crimson-orange** on yellowed paper → use cover mode for blood.
- Knock-out drawn into a plain layer shows as grey crayon → use a dummy canvas.
- Page turn from rectangle strips shows a staircase → an affine transform per strip.
- Double vignette/emboss at a page-to-object transition → page with vignette 0, ramp the outer scene's in.
- Screen-fixed tooth or stains bloat the file → anchor them, don't boil background fills, no ffmpeg grain.
- Reverb IR from unit-variance noise is hugely loud → scale wet to ~18 dB under dry.
- **Channel rule**: violence and abuse are never drawn; imply them (a closed door, an empty room, an object left behind, a blood trace as evidence). No real photos or footage.

## 10. Engine

In `demo/`: `gl.js` (WebGL2 compositor: aged paper with anchored stains, foxing, crease and browned edges; wax adhesion; knock-out; the stain + clear-wax resist; the wash's cover mode for hot-pink blood; the ghost pass for erased drawings; emboss/vignette), `crayon.js` (`line` ribbons with taper, streaks, boil; `fill` hatching with overshoot; `text`; shapes), `rig.js` (occlusion + knock-out parts, limb tubes), `looks.js` (the crayon box). File map and commands: [DEMO.md](DEMO.md#build-notes). Techniques not used there (model sheets, page turn, book on a desk): `$LIB/styles/crayon-book/DEMO.md` and its `demo/`.

## 11. Variation space

You decide the structure, the characters (or none), the page, the opening, the ending, the camera path, the pacing, which crayons from the box, and whether there is a stain. All far from our demo:

- Structures: **a colouring-book page** (all outlines there from frame one; each fact colours one area); **a flip through several pages** (one stage of the case per page, joined by turns); **two drawings of the same day** (what was said, then what happened, the first rubbed out).
- Openings: **a finished page rubbed out** to begin again; **a crayon tip in extreme close-up** mid-stroke, pulling back; **a folded page being opened** along its crease.
- Endings: **the page slipped into a case file**; **one last pink mark** and the music box stopping; **the stain reaching the last clean corner**.

---

How our demo was made (story, shots, score, build): [DEMO.md](DEMO.md). Read it after your treatment exists.
