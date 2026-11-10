#!/bin/zsh
# Baut eine Version aus dem Remotion-Projekt zum fertigen Master (Schritt 6).
#
# Aufruf (im Projektordner schnitt-<videoname>/):
#   bauen.sh --projekt remotion --komposition Reel-v1 --ziel aus/<name>-v1.mp4 \
#            --ton-video schnitt/v1-mix.wav [--entry src/index.ts] [--public-dir public] \
#            [--frames 300] [--neubau] [--gemeinsam-ab 120 --gemeinsam <schlüssel>]
#
#   --projekt      Remotion-Projekt (Kopie der Vorlage), Standard: aktueller Ordner
#   --entry        Einstieg relativ zum Projekt, Standard: src/index.ts
#   --komposition  ID der Komposition, z. B. Reel-v1
#   --ziel         fertige MP4
#   --ton-video    Tonspur daraus nehmen statt sie zu rendern (Mix aus sfx_mix.py oder <v>-hd.mp4)
#   --frames       nur die ersten N Frames bauen (Probe), sonst die ganze Komposition
#   --neubau       zwischengespeicherte Teile verwerfen
#
# Gemeinsamer Teil: Hook-Versionen unterscheiden sich nur vorne, der Body ist Bild für
# Bild gleich. Mit --gemeinsam-ab <frame> --gemeinsam <schlüssel> wird alles ab diesem
# Frame einmal gerendert und von der nächsten Version wiederverwendet. Vorher wird ein
# Standbild gegen den Zwischenspeicher verglichen (PSNR ≥ 40 dB), damit ein falsch
# gesetzter Frame nicht still ein fremdes Video zusammenklebt.
# Welchen Frame nehmen: nicht das Hook-Ende. Der letzte Hook-Untertitel hängt in den Body
# nach, also Hook-Ende plus rund 30 Frames.
#
# Ablauf:
#   1. Platz und Speicher prüfen, daraus die Zahl der Render-Prozesse ableiten
#   2. Ton einmal am Stück (nie stückeln, sonst fehlt an jeder Naht ein AAC-Paket)
#   3. Bild in Teilen rendern, fortsetzbar: fertige Teile werden nicht neu gerendert
#   4. Bei Speicher-Abbruch automatisch mit weniger Prozessen neu
#   5. Teile dekodieren und per Filter kleben, nach Frame-Nummer neu takten
#   6. Master über master.sh, dann Naht- und Taktprüfung
# Danach: abnahme.py auf das Ergebnis.
set -e

SKRIPTE=${0:A:h}
PROJEKT=. ENTRY=src/index.ts KOMP= ZIEL= PUBLIC= FRAMES= TONVIDEO= NEUBAU=0 GEM_AB= GEM_KEY=
while (($#)); do
  case $1 in
    --projekt)      PROJEKT=$2;  shift 2 ;;
    --entry)        ENTRY=$2;    shift 2 ;;
    --komposition)  KOMP=$2;     shift 2 ;;
    --ziel)         ZIEL=$2;     shift 2 ;;
    --public-dir)   PUBLIC=$2;   shift 2 ;;
    --frames)       FRAMES=$2;   shift 2 ;;
    --ton-video)    TONVIDEO=$2; shift 2 ;;
    --neubau)       NEUBAU=1;    shift ;;
    --gemeinsam-ab) GEM_AB=$2;   shift 2 ;;
    --gemeinsam)    GEM_KEY=$2;  shift 2 ;;
    -h|--help)      sed -n '2,32p' "$0"; exit 0 ;;
    *) echo "Unbekannte Option: $1" >&2; exit 2 ;;
  esac
done
[[ -n "$KOMP" && -n "$ZIEL" ]] || { echo "--komposition und --ziel sind Pflicht (--help zeigt alle Optionen)" >&2; exit 2 }
[[ "$ZIEL" == *.mp4 ]] || { echo "Ziel muss .mp4 sein" >&2; exit 2 }
[[ -f "$PROJEKT/package.json" ]] || { echo "Kein Remotion-Projekt: $PROJEKT/package.json fehlt" >&2; exit 2 }

# Vor dem cd ins Projekt absolut machen, sonst zeigen relative Pfade ins Leere.
ZIEL=${ZIEL:a}
[[ -n "$TONVIDEO" ]] && TONVIDEO=${TONVIDEO:a}
PROJEKT=${PROJEKT:a}
mkdir -p "${ZIEL:h}"
SLUG=${${ZIEL:t}:r}
TMP=${TMPDIR:-/tmp}/schnitt-$SLUG
mkdir -p "$TMP"
(( NEUBAU )) && rm -f "$TMP"/teil-*.mp4(N) "$TMP"/ton.wav  # (N): leerer Zwischenspeicher ist kein Fehler
# Python mit numpy für die Prüfungen: Umgebung aus setup.py, SCHNITT_PYTHON überschreibt.
PY=${SCHNITT_PYTHON:-$HOME/.config/schnitt/venv/bin/python}
[[ -x "$PY" ]] || PY=python3
"$PY" -c "import numpy" 2>/dev/null || { echo "Python mit numpy fehlt ($PY). Erst setup.py ausführen." >&2; exit 2 }
cd "$PROJEKT"

if [[ ! -t 1 ]]; then
  echo "== Hinweis: läuft ohne Terminal. Wird der Lauf abgebrochen, bleiben die fertigen Teile liegen,"
  echo "   ein zweiter Aufruf setzt dort fort."
fi

# --- 1. Lage prüfen -----------------------------------------------------------
PLATZ_GB=$(df -Pk "$PROJEKT" | awk 'NR==2 {printf "%d", $4/1048576}')
(( PLATZ_GB >= 5 )) || { echo "Nur ${PLATZ_GB} GB frei, das reicht für einen Render nicht." >&2; exit 1 }
# Wirklich freier Speicher. macOS: frei + inaktiv. Linux: MemAvailable.
# Voller Pfad: in einer Sandbox-Shell liegt sysctl nicht im PATH.
SEITE=$(/usr/sbin/sysctl -n hw.pagesize 2>/dev/null || echo 16384)
frei_mb() {
  if [[ -r /proc/meminfo ]]; then
    awk '/^MemAvailable:/ {printf "%d", $2/1024}' /proc/meminfo
  else
    vm_stat | awk -v s=$SEITE '
      /Pages free/     {f=$3} /Pages inactive/ {i=$3}
      END {gsub(/\./,"",f); gsub(/\./,"",i); printf "%d", (f+i)*s/1048576}'
  fi
}
prozesse() {
  # Ein Remotion-Prozess ist ein Chrome-Tab mit erfahrungsgemäß rund 1,5 GB.
  local c=${CONC:-$(( $(frei_mb) / 1500 ))}
  (( c < 1 )) && c=1
  (( c > 4 )) && c=4
  echo $c
}
# Läuft schon ein Render, wird nicht gestartet: zwei gleichzeitig reißen den Speicher und sterben beide.
# Steht vor dem Aufräumen, sonst würden die Chrome-Prozesse eines laufenden Renders beendet.
if pgrep -f "remotion render" > /dev/null; then
  echo "Es läuft bereits ein Remotion-Render. Erst den abwarten." >&2
  exit 1
fi
# Abgebrochene Renders lassen Remotions Chrome-Prozesse zurück, die den Speicher für den nächsten Lauf fressen.
# Nur die von Remotion, kein anderer Browser.
LEICHEN=$(pgrep -f "remotion/chrome-headless-shell" | wc -l | tr -d ' ')
if (( LEICHEN > 0 )); then
  echo "== ${LEICHEN} alte Chrome-Prozesse von Remotion, werden beendet"
  pkill -f "remotion/chrome-headless-shell" || true
  sleep 3
fi
CONC=$(prozesse)
# Ist der Auslagerungsspeicher fast voll, beendet macOS Prozesse, statt auszulagern.
SWAP=$(/usr/sbin/sysctl -n vm.swapusage 2>/dev/null || echo "")
if [[ -n "$SWAP" ]]; then
  SWAP_FREI=${${SWAP##*free = }%%M*}
  if (( ${SWAP_FREI%.*} < 2000 )); then
    echo "   Auslagerungsspeicher fast voll, Render läuft mit einem Prozess. Dauerhaft hilft ein Neustart." >&2
    CONC=1
  fi
fi
echo "== ${PLATZ_GB} GB Platte frei, $(frei_mb) MB Speicher frei, ${CONC} Prozesse"

# --- Frames ermitteln, wenn nicht angegeben ----------------------------------
if [[ -z "$FRAMES" ]]; then
  FRAMES=$(npx remotion compositions "$ENTRY" ${PUBLIC:+--public-dir=$PUBLIC} 2>/dev/null \
    | awk -v k="$KOMP" '$1==k {print $4}' | head -1)
fi
[[ "$FRAMES" == <-> ]] || { echo "Frame-Anzahl nicht ermittelt, bitte --frames angeben" >&2; exit 1 }
echo "== $FRAMES Frames"

# --- 2. Ton, einmal, am Stück -----------------------------------------------
TON=$TMP/ton.wav
# Zwischengespeicherter Ton aus einem früheren Lauf passt sonst still nicht zum Bild.
if [[ -s "$TON" ]]; then
  TON_S=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$TON")
  python3 -c "import sys; sys.exit(0 if abs($TON_S - $FRAMES/30) <= 0.1 else 1)" \
    || { echo "Ton im Zwischenspeicher ($TON_S s) passt nicht zu $FRAMES Frames, mit --neubau starten" >&2; exit 1 }
fi
# Hat die Komposition eigene Tonelemente, rendert Remotion den Ton selbst und --ton-video bleibt liegen.
# Gesucht wird nur im Quellordner (src/), nie in node_modules: dort liegen Remotions eigene Audio-Komponenten
# und das Bundle von `npm run cues`.
if [[ -n "$TONVIDEO" ]] && grep -rqE --exclude-dir=node_modules "<Audio|<OffthreadAudio|from 'remotion'.*\bAudio\b" "${ENTRY:h}" 2>/dev/null; then
  echo "== ${ENTRY:h}/ enthält ein Audio-Element: Ton wird aus Remotion gerendert, --ton-video bleibt ungenutzt" >&2
  TONVIDEO=
fi
if [[ ! -s "$TON" ]]; then
  if [[ -n "$TONVIDEO" ]]; then
    [[ -f "$TONVIDEO" ]] || { echo "Tonquelle nicht gefunden: $TONVIDEO" >&2; exit 1 }
    LAENGE=$(python3 -c "print($FRAMES/30)")
    echo "== Ton aus $TONVIDEO (${LAENGE} s)"
    ffmpeg -v error -y -i "$TONVIDEO" -vn -t "$LAENGE" -c:a pcm_s16le -ar 48000 "$TON"
    # Gegenprobe: zu kurzer Ton wäre ein stiller Fehler am Dateiende.
    IST_S=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$TON")
    python3 -c "import sys; sys.exit(0 if abs($IST_S - $LAENGE) < 0.05 else 1)" \
      || { echo "Tonspur ist $IST_S s statt $LAENGE s. Passt die Tonquelle zur Komposition?" >&2; exit 1 }
  else
    # Remotion schickt auch für --codec=wav jeden Frame durch Chrome, das dauert. Mit --ton-video geht es in Sekunden.
    echo "== Ton rendern (Chrome läuft über jeden Frame)"
    npx remotion render "$ENTRY" "$KOMP" "$TON" ${PUBLIC:+--public-dir=$PUBLIC} --codec=wav \
      --frames=0-$((FRAMES - 1)) > "$TMP/ton.log" 2>&1 \
      || { echo "Ton-Render fehlgeschlagen, Log: $TMP/ton.log" >&2; tail -20 "$TMP/ton.log" >&2; exit 1 }
  fi
fi
[[ -s "$TON" ]] || { echo "Keine Tonspur erzeugt." >&2; exit 1 }

# --- 3./4. Bild in Teilen, fortsetzbar, mit Rückfall -------------------------
# Rund 400 Frames je Teil: klein genug, dass ein Abbruch wenig kostet, groß genug, dass der Start nicht dominiert.
PRO_TEIL=${PRO_TEIL:-400}

rendere_teil() {          # $1 = Zieldatei, $2 = von, $3 = bis, $4 = Prozesse
  npx remotion render "$ENTRY" "$KOMP" "$1" ${PUBLIC:+--public-dir=$PUBLIC} --codec=h264 --crf=17 \
    --concurrency=$4 --frames=$2-$3 > "${1:r}.log" 2>&1
}

# Rendert einen Frame-Bereich in Stücken nach $1 und hängt die Dateien an STUECKE an.
# Fertige Stücke mit richtiger Bildzahl werden übersprungen.
rendere_bereich() {       # $1 = Ordner, $2 = erster Frame, $3 = letzter Frame
  local ORDNER=$1 A=$2 B=$3
  local SPANNE=$(( B - A + 1 ))
  local N=$(( (SPANNE + PRO_TEIL - 1) / PRO_TEIL ))
  (( N < 1 )) && N=1
  mkdir -p "$ORDNER"
  local k VON BIS SOLL IST VERSUCH VERSUCH_CONC ERFOLG DATEI
  for ((k = 0; k < N; k++)); do
    VON=$(( A + SPANNE * k / N ))
    BIS=$(( A + SPANNE * (k + 1) / N - 1 ))
    SOLL=$(( BIS - VON + 1 ))
    DATEI="$ORDNER/teil-$k.mp4"
    STUECKE+=("$DATEI")
    if [[ -s "$DATEI" ]]; then
      # ffprobe hängt manchmal ein leeres CSV-Feld an ("176,"), cut nimmt nur die Zahl.
      IST=$(ffprobe -v error -select_streams v -count_frames \
            -show_entries stream=nb_read_frames -of csv=p=0 "$DATEI" 2>/dev/null | cut -d, -f1 || echo 0)
      if [[ "$IST" == "$SOLL" ]]; then echo "== ${ORDNER:t}/Teil $k schon da ($IST Frames)"; continue; fi
      rm -f "$DATEI"
    fi
    echo "== ${ORDNER:t}/Teil $k: Frames $VON-$BIS"
    VERSUCH_CONC=$CONC
    ERFOLG=0
    for VERSUCH in 1 2 3; do
      if rendere_teil "$DATEI" $VON $BIS $VERSUCH_CONC; then ERFOLG=1; break; fi
      # Nur Speicher-Abbrüche neu versuchen, alles andere ist ein echter Fehler im Code.
      if grep -qiE "out of memory|ENOMEM|Killed|signal 9|SIGKILL|Target closed|Protocol error|Cannot allocate" "${DATEI:r}.log"; then
        VERSUCH_CONC=$(( VERSUCH_CONC > 1 ? VERSUCH_CONC - 1 : 1 ))
        echo "   Speicher-Abbruch, neuer Versuch mit $VERSUCH_CONC Prozess(en)" >&2
        sleep 10
      else
        echo "Render-Fehler in ${ORDNER:t}/Teil $k, Log: ${DATEI:r}.log" >&2
        tail -25 "${DATEI:r}.log" >&2
        exit 1
      fi
    done
    (( ERFOLG )) || { echo "Teil $k auch mit einem Prozess nicht gerendert. Rechner neu starten oder PRO_TEIL=200 setzen." >&2; exit 1 }
  done
}

# Prüft, ob ein gefüllter gemeinsamer Zwischenspeicher zu dieser Version passt: Standbild rendern,
# PSNR gegen den ersten gespeicherten Frame. Ab 40 dB ist es dasselbe Bild.
cache_passt() {           # $1 = Ordner, $2 = erster gemeinsamer Frame
  local ORDNER=$1 AB=$2
  [[ -s "$ORDNER/teil-0.mp4" ]] || return 0
  local PROBE="$ORDNER/probe-$SLUG.png" REF="$ORDNER/probe-ref.png" WERT
  npx remotion still "$ENTRY" "$KOMP" "$PROBE" ${PUBLIC:+--public-dir=$PUBLIC} --frame=$AB > "$ORDNER/probe.log" 2>&1 \
    || { echo "   Standbild für die Probe nicht gerendert, Log: $ORDNER/probe.log" >&2; return 1 }
  ffmpeg -v error -y -i "$ORDNER/teil-0.mp4" -frames:v 1 "$REF"
  WERT=$(ffmpeg -hide_banner -i "$PROBE" -i "$REF" -lavfi psnr -f null - 2>&1 \
         | grep -oE "average:[0-9.]+|average:inf" | head -1 | cut -d: -f2)
  rm -f "$PROBE" "$REF"
  [[ -n "$WERT" ]] || { echo "   PSNR nicht messbar." >&2; return 1 }
  if [[ "$WERT" == inf ]] || (( $(python3 -c "print(1 if float('$WERT') >= 40 else 0)") )); then
    echo "== gemeinsamer Teil passt (PSNR $WERT dB)"
    return 0
  fi
  echo "== gemeinsamer Teil passt nicht (PSNR $WERT dB), wird neu gebaut" >&2
  return 1
}

STUECKE=()
if [[ -n "$GEM_AB" ]]; then
  [[ "$GEM_AB" == <-> && "$GEM_AB" -gt 0 && "$GEM_AB" -lt "$FRAMES" ]] \
    || { echo "--gemeinsam-ab muss zwischen 1 und $((FRAMES-1)) liegen" >&2; exit 2 }
  [[ -n "$GEM_KEY" ]] || { echo "--gemeinsam-ab braucht --gemeinsam <schlüssel>" >&2; exit 2 }
  GEMDIR=${TMPDIR:-/tmp}/schnitt-gemeinsam-$GEM_KEY
  GEM_LAENGE=$(( FRAMES - GEM_AB ))
  (( NEUBAU )) && rm -rf "$GEMDIR"
  mkdir -p "$GEMDIR"
  # Ein Body anderer Länge ist ein anderer Body.
  if [[ -f "$GEMDIR/laenge" && "$(cat "$GEMDIR/laenge")" != "$GEM_LAENGE" ]]; then
    echo "== gemeinsamer Teil hat $(cat "$GEMDIR/laenge") statt $GEM_LAENGE Frames, wird neu gebaut" >&2
    rm -f "$GEMDIR"/teil-*.mp4(N)
  fi
  cache_passt "$GEMDIR" "$GEM_AB" || rm -f "$GEMDIR"/teil-*.mp4(N)
  echo "$GEM_LAENGE" > "$GEMDIR/laenge"
  echo "== eigener Teil: Frames 0-$((GEM_AB-1)) | gemeinsamer Teil: $GEM_LAENGE Frames ab $GEM_AB"
  rendere_bereich "$TMP" 0 $((GEM_AB - 1))
  rendere_bereich "$GEMDIR" $GEM_AB $((FRAMES - 1))
else
  rendere_bereich "$TMP" 0 $((FRAMES - 1))
fi

# --- 5. Teile kleben ----------------------------------------------------------
# concat -c copy auf MP4 addiert Container-Dauern und lässt pro Naht ein Loch, roher H.264 verschiebt das
# Bild bei B-Frames gegen den Ton. Deshalb: jedes Stück dekodieren, per Filter aneinanderhängen und nach
# Frame-Nummer neu takten. Keine fremden Zeitstempel, Versatz 0.
EING=() KETTE=""
for ((i = 1; i <= ${#STUECKE[@]}; i++)); do
  EING+=(-i "${STUECKE[$i]}")
  KETTE+="[$((i - 1)):v]"
done
ffmpeg -v error -y "${EING[@]}" \
  -filter_complex "${KETTE}concat=n=${#STUECKE[@]}:v=1:a=0,setpts=N/(30*TB)[v]" \
  -map "[v]" -r 30 -c:v libx264 -crf 10 -preset veryfast -pix_fmt yuv420p "$TMP/bild.mov"
ffmpeg -v error -y -i "$TMP/bild.mov" -i "$TON" -map 0:v -map 1:a -c:v copy -c:a pcm_s16le "$TMP/roh.mov"

IST=$(ffprobe -v error -select_streams v -count_frames -show_entries stream=nb_read_frames -of csv=p=0 "$TMP/roh.mov" | cut -d, -f1)
[[ "$IST" == "$FRAMES" ]] || { echo "Frame-Anzahl stimmt nicht: $IST statt $FRAMES" >&2; exit 1 }

# --- 6. Master und Prüfungen -------------------------------------------------
zsh "$SKRIPTE/master.sh" "$TMP/roh.mov" "$ZIEL"
"$PY" "$SKRIPTE/naht_check.py" "$ZIEL"
# Taktprüfung: bei 30 fps muss jeder Paketabstand 0,0333 s sein. Fängt Sync-Fehler, die der Naht-Check nicht sieht.
ffprobe -v error -select_streams v -show_entries packet=pts_time -of csv=p=0 "$ZIEL" \
  | sort -n | awk 'NR>1{d=$1-p; if(d>0.0334||d<0.0333){print "LÜCKE bei", $1; n++}} {p=$1}
                   END{if(n) exit 1}' \
  || { echo "Takt stimmt nicht, Bild und Ton laufen auseinander." >&2; exit 1 }
echo "== fertig: $ZIEL"
echo "   Nächster Schritt: $PY $SKRIPTE/abnahme.py \"$ZIEL\" --fix"
exit 0
