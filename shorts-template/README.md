# Shorts template (3-zone layout, Remotion)

Fixed layout for 1080x1920 story shorts:

| zone | y | rule |
|---|---|---|
| Title | 0–400 | hook title, pinned for the whole video |
| Stage | 400–1480 | square illustration stage; all visuals live here |
| Subtitle | 1480–1920 | one line, always at the same spot; quotes get a speaker tag |

Rules baked into the components:
- Type: Pretendard only, 4 sizes (`theme.ts` `SIZE`), one accent colour (`C.accent`).
- On-stage text: a single chip slot at the stage's top-left (`Chip`), one per shot.
- Motion: `enter` (fade + rise), `pop` (small overshoot), `kenBurns` (slow drift); nothing else.
- Transition: one type (push from the right, 9 frames).
- Characters stand on one ground line (`GROUND`) and keep the same asset per role.

Workflow:
1. TTS segments → `scripts/segments_full.json` (scene, speaker, text, word timings).
2. `npm run data` → `src/data.json` (timeline + balanced one-line subtitle chunks).
3. Scenes in `src/scenes.tsx`, highlight phrases in `HIGHLIGHT`.
4. `npm run render` → `out/story.mp4` (rendered, then loudness-normalised to -14 LUFS).

`npx remotion studio` opens a live preview.
