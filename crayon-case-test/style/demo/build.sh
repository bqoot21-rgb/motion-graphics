#!/bin/sh
# Rebuild the Crayon Case demo film from scratch: sh build.sh   (runs from any directory)
# Writes into ${OUT:-~/crayon-case-build}; this folder is left as it is (events.json is regenerated identically).
set -e
LIB=${LIB:-$HOME/lemo-opuscar}   # the Lemo-Opuscar library
D=$(cd "$(dirname "$0")" && pwd)
OUT=${OUT:-$HOME/crayon-case-build}; mkdir -p "$OUT"
cd "$LIB"
node core/render/events.mjs "$D"                                                    # 1. timeline → events.json (drawing, erasing, stain, pink cues)
LIB="$LIB" .venv/bin/python "$D/audio.py" "$D"                                       # 2. score + foley + mix → mix.wav
mv "$D/mix.wav" "$OUT/mix.wav"
node core/render/video.mjs "$D" --fps 24 --workers 3 --out "$OUT/video24.mp4"        # 3. frame-by-frame render (no subtitles: they are burned in later)
sh core/render/mux.sh "$OUT/video24.mp4" "$OUT/mix.wav" "$OUT/test.mp4" 24 0  # 4. mux + −14 LUFS (the paper is the grain)
node core/render/still.mjs "$D" 25.6 --out "$OUT" --prefix poster_                  # 5. poster
echo "film: $OUT/test.mp4"
