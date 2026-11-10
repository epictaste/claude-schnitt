# Schritt 1: Voraussetzungen

**Was ein Cutter hier macht:** Arbeitsplatz einrichten, Material sichten, Format klären.
**Warum das Video es braucht:** Ohne Wortzeiten landet kein Schnitt und keine Grafik auf dem richtigen Wort.

## Was gebraucht wird

| Was | Wofür | Wer installiert |
|---|---|---|
| Claude Pro oder Max | Schneiden kostet viele Token, wer regelmäßig schneidet, braucht mehr Limit | der Nutzer |
| Claude Code (Terminal oder Code-Tab der Desktop-App) | hier läuft der Skill, programmiert wird nicht | der Nutzer |
| Deepgram-Konto mit API-Schlüssel | Transkript mit Zeitstempel für jedes einzelne Wort, darauf baut alles auf | der Nutzer legt das Konto an, `setup.py` legt die Datei an |
| ffmpeg und ffprobe | schneiden, messen, Ton mischen | `setup.py` über brew |
| Node 20 oder neuer | Remotion, der Baukasten für Grafiken und Untertitel | `setup.py` über brew |
| Python-Umgebung mit numpy und pillow | Pegelmessung, Standbilder | `setup.py` unter `~/.config/schnitt/venv` |
| Augen-Werkzeug (macOS Vision) | Augenhöhe je Clip | `setup.py` kompiliert es mit swiftc |

Der Skill ist für den Mac gebaut. Auf anderen Systemen laufen Schritt 1 bis 5, das Augen-Werkzeug fehlt.

## Ablauf

```bash
python3 "$SKILL_DIR/scripts/setup.py" --check     # Exit 0 = alles da
python3 "$SKILL_DIR/scripts/setup.py"             # installiert, was fehlt
python3 "$SKILL_DIR/scripts/setup.py" --json      # volles Bild, wenn etwas unklar ist
```

Fehlt der Schlüssel, legt `setup.py` die Datei `~/.config/schnitt/.env` mit Rechten 0600 an. Der
Nutzer trägt dort ein:

```
DEEPGRAM_API_KEY=<sein Schlüssel>
```

Wer schon einen Schlüssel in `~/.config/watch/.env` hat, muss nichts tun, der wird mitgelesen.
Den Schlüssel nie in den Chat holen, nie ausgeben, nie in eine Datei im Projekt schreiben.

## Material

- Rohvideo als lokale Datei. Für Schritt 3 bis 6 hochkant (9:16), für „nur rohschnitt“ geht jedes Format.
- iPhone-Videos sind oft HDR (HLG) und haben eine schwankende Bildrate. Die Skripte rechnen beim
  Schneiden auf 30 Bilder pro Sekunde und SDR um, der Nutzer muss nichts vorher umwandeln.
- Hilfreich, aber nicht nötig: das Skript, das er abgelesen hat. Damit fallen fehlende Wörter auf.

## Video ansehen

Bevor irgendetwas geplant wird, ein paar Frames ziehen und lesen:

```bash
for t in 1 5 15 30 60; do
  ffmpeg -v error -y -ss $t -i "$VIDEO" -frames:v 1 -vf scale=540:-2 "$P/aus/blick-$t.jpg"
done
```

Merken: Format, Licht (dunkel, Gegenlicht), wo der Kopf sitzt, ob Untertitel eingebrannt sind,
ob mehrere Hooks hintereinander gesprochen wurden.

**Prüfpunkt:** `setup.py --check` gibt 0 zurück, Projektordner existiert.
