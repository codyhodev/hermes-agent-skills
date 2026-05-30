#!/usr/bin/env bash
# Voice Command Pipeline — one-shot recording + transcribe + clean
# Usage: bash scripts/voice_cmd_pipeline.sh [duration_seconds]
# Records for N seconds (default 10), transcribes, cleans, prints result.

set -euo pipefail

DURATION="${1:-10}"
RAW="/tmp/voice_cmd.raw"
WAV="/tmp/voice_cmd.wav"

# Clean previous
rm -f "$RAW" "$WAV"

echo "🎤 Recording for ${DURATION}s…"
parec --rate=16000 --channels=1 --format=s16le --raw > "$RAW" &
PID=$!
sleep "$DURATION"
kill "$PID" 2>/dev/null
wait "$PID" 2>/dev/null || true

echo "🔊 Converting + noise reduction…"
ffmpeg -f s16le -ar 16000 -ac 1 -i "$RAW" \
       -af "highpass=f=200,lowpass=f=4000,afftdn=nr=15:nf=-30" \
       -y "$WAV" 2>/dev/null

echo "📝 Transcribing…"
RESULT=$(echo '{"action":"transcribe","file_path":"'"$WAV"'"}' | \
         nc -U -w 30 ~/.hermes/run/funasrd.sock 2>/dev/null)

echo "--- RAW RESULT ---"
echo "$RESULT"

# Extract transcript field if JSON
if command -v python3 &>/dev/null; then
    echo "$RESULT" | python3 -c "
import sys, json
try:
    d = json.loads(sys.stdin.read().strip())
    print('--- CLEANED ---')
    print(d.get('transcript', '(no transcript)'))
except: pass
"
fi
