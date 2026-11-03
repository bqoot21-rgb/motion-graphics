#!/bin/sh
# Rebuild this test from scratch: sh build.sh   (runs from any directory)
set -e
LIB=${LIB:-$HOME/lemo-opuscar}
D=$(cd "$(dirname "$0")" && pwd); OUT=${OUT:-$D/out}; mkdir -p "$OUT"
cd "$LIB"
.venv/bin/python core/tts/tts.py "$D/lines.json" "$D/voices"                          # 1. narration (Kokoro am_michael)
node core/render/events.mjs "$D"                                                       # 2. timeline → events.json
LIB="$LIB" .venv/bin/python "$D/audio.py" "$D" && mv "$D/mix.wav" "$OUT/mix.wav"       # 3. score + foley + voice + mix
.venv/bin/python core/render/srt.py "$D/subs.json" "$D/sinsa-test.srt"                 # 4. subtitles file (they are also burned into the picture)
node core/render/video.mjs "$D" --fps 24 --workers 3 --out "$OUT/video24.mp4"           # 5. frames
sh core/render/mux.sh "$OUT/video24.mp4" "$OUT/mix.wav" "$D/sinsa-test.mp4" 24 0       # 6. mux + −14 LUFS
