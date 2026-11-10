#!/bin/zsh
# Macht aus dem Render den Master für Instagram, TikTok und YouTube Shorts (Schritt 6, ruft bauen.sh auf).
# Ton auf -14 LUFS / -1 dBTP, Bild als bt709 getaggt, faststart, feste Bildrate.
# fps_mode cfr ist Pflicht: ohne das verschluckt der Encoder bei Quellen mit Edit-List den ersten
# Frame und alles danach liegt 33 ms vor dem Ton.
#
# Aufruf: master.sh <render.mov|mp4> [ausgabe.mp4]
#   KLANG=neutral master.sh ...                 nur Lautheit, kein EQ und kein Kompressor
#   ENTRAUSCHEN=1 master.sh ...                 bei Hintergrundgeräuschen (braucht ein RNNoise-Modell,
#                                               Pfad in RNNOISE_MODELL)
#   MUSIK=teppich.wav MUSIK_PEGEL=-6dB master.sh ...   Hintergrundmusik, wird unter der Stimme geduckt
set -e
IN=$1
[[ -f "$IN" ]] || { echo "Datei fehlt: $IN" >&2; exit 2 }
OUT=${2:-${IN:r}-master.mp4}

# Klangkette für ein Ansteckmikro: Wärme rauf, Schärfe zwischen 4 und 8 kHz runter, dann sanft verdichten.
EQ="highpass=f=70,equalizer=f=250:width_type=q:w=1.0:g=3,equalizer=f=5000:width_type=q:w=1.2:g=-3.5,treble=g=4:f=11000:width_type=q:width=0.6"
KOMP="acompressor=threshold=-24dB:ratio=3:attack=5:release=120:makeup=3"
KETTE="$EQ,$KOMP"
[[ "$KLANG" == neutral ]] && KETTE="highpass=f=70"
if [[ -n "$ENTRAUSCHEN" ]]; then
  MODELL=${RNNOISE_MODELL:-$HOME/.local/share/rnnoise/sh.rnnn}
  [[ -f "$MODELL" ]] || { echo "RNNoise-Modell fehlt: $MODELL (Pfad per RNNOISE_MODELL setzen)" >&2; exit 1 }
  # Pfad mit Komma, Doppelpunkt oder Hochkomma würde den Filtergraphen brechen: Modell unter sicherem Namen verlinken.
  SICHER=$(mktemp -d)/rnnoise.rnnn
  ln -s "${MODELL:A}" "$SICHER"
  KETTE="arnndn=m=$SICHER,$KETTE"   # vor den Kompressor, sonst hebt der das Rauschen mit an
fi

# Der Master darf genau einen Frame länger sein als der Render: -fps_mode cfr füllt eine gerundete
# Quelldauer mit einem Duplikat des letzten Bildes auf (33 ms Standbild am Ende, sonst nichts).
# Mehr als einer hieße kaputte Zeitstempel, das prüft das Ende dieses Skripts.
FRAMES=$(ffprobe -v error -select_streams v -count_frames -show_entries stream=nb_read_frames -of csv=p=0 "$IN" | cut -d, -f1)
[[ "$FRAMES" == <-> ]] || { echo "Frame-Anzahl der Quelle nicht lesbar: $IN" >&2; exit 1 }

# Farbtags: ffmpeg schreibt -color_primaries/-color_trc nur, wenn die Frames sie selbst tragen, deshalb setparams.
# Nur diese zwei Tags setzen: der Remotion-Render ist Vollbereich, range=tv würde ihn nur umbenennen statt
# umrechnen. Die Umrechnung macht -color_range tv.
FARBE="setparams=color_primaries=bt709:color_trc=bt709"

# Durchgang 1: Ton nach der Kette messen
M=$(ffmpeg -nostats -i "$IN" -af "$KETTE,loudnorm=I=-14:TP=-1:LRA=11:print_format=json" -f null - 2>&1 | sed -n '/^{/,/^}/p')
wert() { echo "$M" | grep "\"$1\"" | sed 's/.*: "//;s/".*//' }

# Durchgang 2: normalisieren und kodieren.
# Mit MUSIK läuft loudnorm nur auf der Stimme, die Summe kann etwas lauter werden; abnahme.py --fix holt das zurück.
if [[ -n "$MUSIK" ]]; then
  [[ -f "$MUSIK" ]] || { echo "Musikdatei fehlt: $MUSIK" >&2; exit 1 }
  PEGEL=${MUSIK_PEGEL:-0dB}
  ffmpeg -v error -y -i "$IN" -i "$MUSIK" \
    -filter_complex "[0:a]${KETTE},loudnorm=I=-14:TP=-1:LRA=11,asplit=2[v][key];[1:a]volume=$PEGEL,afade=t=in:d=2[m0];[m0][key]sidechaincompress=threshold=0.04:ratio=8:attack=25:release=450[duck];[v][duck]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.84:latency=true[aus];[0:v]${FARBE}[bild]" \
    -map "[bild]" -map "[aus]" \
    -c:a aac -b:a 256k -ar 48000 \
    -fps_mode cfr -c:v libx264 -profile:v high -preset slow -crf 18 -maxrate 12M -bufsize 24M \
    -pix_fmt yuv420p -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv \
    -movflags +faststart "$OUT"
else
  ffmpeg -v error -y -i "$IN" -vf "$FARBE" \
    -af "$KETTE,loudnorm=I=-14:TP=-1:LRA=11:measured_I=$(wert input_i):measured_TP=$(wert input_tp):measured_LRA=$(wert input_lra):measured_thresh=$(wert input_thresh):offset=$(wert target_offset):linear=true" \
    -c:a aac -b:a 256k -ar 48000 \
    -fps_mode cfr -c:v libx264 -profile:v high -preset slow -crf 18 -maxrate 12M -bufsize 24M \
    -pix_fmt yuv420p -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv \
    -movflags +faststart "$OUT"
fi

echo "== $OUT"
IST=$(ffprobe -v error -select_streams v -count_frames -show_entries stream=nb_read_frames -of csv=p=0 "$OUT" | cut -d, -f1)
(( IST == FRAMES || IST == FRAMES + 1 )) \
  || { echo "Master hat $IST Frames, Quelle $FRAMES. Mehr als ein aufgefüllter Frame heißt kaputte Zeitstempel." >&2; exit 1 }
ffmpeg -nostats -i "$OUT" -af ebur128=peak=true -f null - 2>&1 | grep -A4 "Summary:" | grep "I: "
ls -lh "$OUT" | awk '{print "Größe:", $5}'
