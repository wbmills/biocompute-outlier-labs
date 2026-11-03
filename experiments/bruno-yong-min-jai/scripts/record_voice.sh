#!/usr/bin/env bash
# Record your own "yes" / "no" takes from the Mac microphone (1.5 s each, 16 kHz mono).
# Usage: ./scripts/record_voice.sh <your_name> [takes_per_word=10]   (MIC=":<device name>" for another input;
# list them with: ffmpeg -f avfoundation -list_devices true -i "")
# Files go to data/audio/human/ (git-ignored). Speakers are held out whole when testing.
set -euo pipefail
cd "$(dirname "$0")/.."
NAME=${1:?usage: record_voice.sh <your_name> [takes]}; N=${2:-10}; MIC=${MIC:-":MacBook Pro Microphone"}
NAME=$(echo "$NAME" | tr -cd '[:alnum:]')
OUT=data/audio/human; mkdir -p "$OUT"
for k in $(seq -w 1 "$N"); do
  if [ $((10#$k % 2)) -eq 1 ]; then ORDER="yes no"; else ORDER="no yes"; fi   # alternate so order can't leak
  for w in $ORDER; do
    f="$OUT/${w}_${NAME}_${k}.wav"
    read -r -p "Take $k/$N: press Enter, then say \"$w\" " _
    ffmpeg -loglevel error -y -f avfoundation -i "$MIC" -t 1.5 -ac 1 -ar 16000 "$f"
    echo "  saved $f"
  done
done
