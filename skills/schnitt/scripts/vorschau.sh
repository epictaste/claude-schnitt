#!/bin/zsh
# Kleine 720p-Vorschau eines Masters zum Anschauen am Handy oder im Browser (Schritt 6).
# Der Master selbst bleibt unangetastet.
#
# Aufruf: vorschau.sh <master.mp4> [ausgabe.mp4]
# Standard-Ausgabe: <master>-vorschau.mp4 daneben. Öffnen auf dem Mac: open <datei>
set -e
IN=$1
[[ -f "$IN" ]] || { echo "Datei fehlt: $IN" >&2; exit 2 }
OUT=${2:-${IN:r}-vorschau.mp4}
ffmpeg -v error -y -i "$IN" -vf "scale=720:-2:flags=lanczos" -c:v libx264 -preset fast -crf 25 -maxrate 2500k -bufsize 5M \
  -fps_mode cfr -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart "$OUT"
echo "== Vorschau $OUT ($(( $(wc -c < "$OUT") / 1048576 )) MB)"
