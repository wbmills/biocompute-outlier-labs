#!/usr/bin/env bash
# Synthetic speech dataset: macOS text-to-speech voices saying "yes" / "no" at two speaking rates.
# This is NOT human speech; reports label it "synthetic speech (macOS say)".
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=data/audio/tts; mkdir -p "$OUT"
VOICES="Albert Aman Daniel Eddy Flo Fred Grandma Grandpa Junior Karen Kathy Moira Ralph Reed Rishi Rocko Samantha Sandy Shelley Tara Tessa"
for v in $VOICES; do
  for r in 160 220; do
    for w in yes no; do
      say -v "$v" -r "$r" --file-format=WAVE --data-format=LEI16@16000 -o "$OUT/${w}_${v}_r${r}.wav" "$w"
    done
  done
done
echo "$(ls "$OUT"/*.wav | wc -l | tr -d ' ') files in $OUT"
