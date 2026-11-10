# Schritt 6: Schnitt und Feinschliff

**Was ein Cutter hier macht:** Farbe, Zoom, Ton, Export und Endkontrolle.
**Warum das Video es braucht:** Das ist der Unterschied zwischen „selbst geschnitten“ und „sieht professionell aus“.

## 1. Licht

```bash
"$PY" "$SKILL_DIR/scripts/licht.py" "$R/schnitt-hd.mp4" "$P/aus/licht" --zeit 20
"$PY" "$SKILL_DIR/scripts/licht.py" --waehle 3 --grade-datei "$P/schnitt/grade.txt"   # nach der Wahl
```

Fünf Varianten am selben Body-Frame (`--zeit` in Sekunden, von kräftig bis sehr hell), je mit
gemessener Gesichtshelligkeit, als `licht-bogen.jpg` in `$P/aus/licht/`. Das Licht hängt von der
Aufnahme ab, also jedes Mal fragen. Empfehlung ist die Variante, deren Gesicht weder fahl noch
ausgebrannt wirkt. `--waehle` schreibt die Wahl nach `schnitt/grade.txt` (ein ffmpeg-Filter).

## 2. HD-Takes und Augen

```bash
"$PY" "$SKILL_DIR/scripts/hd_take.py" "$R" --ziel "$P/schnitt"
"$PY" "$SKILL_DIR/scripts/augen_messen.py" "$P/schnitt"
"$PY" "$SKILL_DIR/scripts/geruest.py" "$P/spec.json"
for f in "$P"/schnitt/v*-hd.mp4; do ln -f "$f" "$P/remotion/public/video/$(basename "$f")"; done
```

- `hd_take.py` baut je Version aus `schnitt/bereiche.json` ein `v*-hd.mp4` in höherer Auflösung als
  das Ziel, damit der Zoom nicht hochskaliert, mit dem Licht aus `grade.txt` und dem Ton aus `v*-neu.mp4`.
- `augen_messen.py` misst Augenhöhe und Gesichtsmitte je Take-Clip (macOS Vision) und schreibt
  `schnitt/augen.json`. Die Vorlage verschiebt jeden Clip so, dass die Augen auf derselben Höhe und
  das Gesicht in der Mitte liegen. Nie eine geschätzte Augenhöhe für das ganze Video nehmen.
- Hardlink (`ln`), kein Symlink: Remotion folgt Symlinks beim Kopieren nicht, der Render bricht ab.

## 3. Zoom

- Im Hook zoomt die Kamera über Satz 1 weich hinein, ab dem ersten Schnitt springt sie.
- Im Body wechselt der Zoom an jedem Take-Schnitt zwischen weit und nah. Der Sprung genau auf dem
  Schnitt verdeckt den Schnitt.
- **Jede Version bekommt ein eigenes Zoom-Level**, über das ganze Video. Plattformen melden zwei
  bildgleiche Videos als Duplikat. Ein Unterschied von 0,05 bis 0,1 reicht, lieber etwas weiter raus
  als zu nah. Je Version ein Standbild zeigen, der Nutzer bestätigt. Werte in `spec.json`, dann
  `geruest.py` erneut.

## 4. Sounds

```bash
(cd "$P/remotion" && npm run -s cues -- v1 > "$P/schnitt/v1-cues.json")
S2=$("$PY" -c "import json; print(json.load(open('$P/schnitt/meta.json'))['SATZ2']['v1'] / 30)")
"$PY" "$SKILL_DIR/scripts/sfx_mix.py" "$P/schnitt/v1-neu.mp4" "$P/schnitt/v1-cues.json" "$S2" "$P/schnitt/v1-mix.wav"
```

`S2` ist der erste harte Schnitt in Sekunden (`SATZ2` aus `meta.json` durch 30). Ergebnis ist
`v1-mix.wav`: Stimme aus dem Original plus Effekte, 48 kHz.

- Die Cues kommen aus den Szenen, alle mit demselben Pegel. Einzelne Lautstärken aus den Szenen
  zählen nicht, sie lagen in der Praxis über der Stimme.
- `sfx_mix.py` legt einen Riser über Satz 1 mit Spitze auf dem ersten Schnitt, einen Whoosh direkt
  danach und die Effekte des Body darunter. Die Sounds erzeugt `sfx.py` per ffmpeg, es gibt keine
  Sound-Bibliothek. Einzelne Effekte höchstens einer pro 0,8 s, Ketten (Nachrichten, Tippen) bleiben ganz.
- Ziel: Effekt-Spitzen im Mittel 3 bis 4 dB unter den Stimm-Spitzen. Nach dem Mischen nachmessen.
- **Ehrlich sagen:** Sounds kann Claude nicht hören. Der Nutzer hört die Mischung selbst an und sagt,
  was zu laut, zu viel oder unpassend ist.
- Im Remotion-Projekt gibt es kein Audio-Element, auch nicht im Kommentar. Sonst rendert der Bau den
  Ton aus Remotion und ignoriert die Mischung.

## 5. Bauen

```bash
zsh "$SKILL_DIR/scripts/bauen.sh" --projekt "$P/remotion" --komposition Reel-v1 \
  --ziel "$P/aus/v1.mp4" --ton-video "$P/schnitt/v1-mix.wav" --frames 300
```

- Erst ein kurzes Stück (`--frames 300`, 10 s) bauen und ansehen. Sitzt das, ohne `--frames` und mit
  `--neubau` das ganze Video (der zwischengespeicherte Ton der Probe ist sonst zu kurz).
- `bauen.sh` rendert in Teilen und setzt nach einem Abbruch beim letzten fertigen Teil fort. Es nimmt
  den Ton aus `--ton-video`, klebt die Teile ohne Lücke, prüft Bildanzahl und Takt und ruft am Ende
  `master.sh` (Ton-Kette, Lautheit, Farbtags für Instagram, TikTok, YouTube Shorts).
- Versionen nacheinander bauen, nie zwei Renders gleichzeitig: das reißt den Speicher.
- Rendern dauert. Ein Video mit drei Versionen kann inklusive der Entscheidungen zwischendurch
  mehrere Stunden brauchen. Plan Zeit und Token ein.

## 6. Endkontrolle

```bash
"$PY" "$SKILL_DIR/scripts/abnahme.py" "$P/aus/v1.mp4" --take "$P/schnitt/v1-hd.mp4" --fix
zsh "$SKILL_DIR/scripts/vorschau.sh" "$P/aus/v1.mp4"
```

`abnahme.py` prüft und schreibt `v1-abnahme.md` und einen Kontaktbogen `v1-abnahme.jpg`:

| Prüfung | Bei Befund |
|---|---|
| Format, Bildrate, Takt | rot, neu bauen |
| Lautheit, Spitzen, Farbtags | `--fix` repariert selbst |
| Tonlöcher, eingefrorene oder falsche Frames zwischen Takes | rot, Stelle melden, Schnitt fixen |
| Helligkeitssprung zwischen Takes, Farbstich Master gegen Take | gelb, melden |
| Lautstärke gleichmäßig, Bild-Ton-Sync | gelb oder rot, melden |
| Helligkeit des Takes, Sync bei gezoomtem Take | nur Hinweis (ℹ️), das Licht hat der Nutzer gewählt |

Vollbild-Passagen liest die Abnahme aus `reel.ts`, dort stehen Grafiken gewollt still.

Technik repariert `--fix`. Alles Inhaltliche meldest du mit Zeitstempel und einem
Fix-Vorschlag, still weggemacht wird nichts. Den Kontaktbogen selbst lesen: Plakat nicht unter der Kopfzeile,
Untertitel nicht im Gesicht, kein Platzhalter, kein Text am Rand.

`vorschau.sh` schreibt eine 720p-Datei neben den Master, zum Ansehen auf dem Handy (AirDrop oder
Cloud-Ordner, das macht der Nutzer). Der Skill verschickt nichts.

## 7. Hook-Versionen

Jede Version durchläuft Bauen und Endkontrolle einzeln. Am Ende in einer Zeile je Version sagen,
was sie unterscheidet (Hook-Text, Zoom), und die Pfade der Master, Abnahmen und Vorschauen nennen.
Welche Version gepostet wird und wann, entscheidet der Nutzer.

**Prüfpunkt:** Abnahme jeder Version grün oder gelbe Befunde gemeldet, Vorschau angesehen, Nutzer sagt „fertig“.
