---
name: schnitt
version: "2.0.0"
description: Schneidet ein selbst gedrehtes Video (Person spricht in die Kamera) in sechs Schritten zum fertigen Hochkant-Video. Rohschnitt mit den besten Takes, Stil aus Referenzvideos, Standbilder zum Abnicken, Storyboard mit Grafiken, die der Nutzer auswählt, dann Licht, Zoom auf jedem Schnitt, Augen auf gleicher Höhe, wortgenaue Untertitel, Sounds, mehrere Hook-Versionen und Endkontrolle. Nutzen, wenn jemand sagt „schneid mein Video“, „mach einen Rohschnitt“, „such die besten Takes“, „Grafiken über mein Video“, „drei Hook-Versionen“, oder eine lokale Videodatei zum Schneiden übergibt. Mit „nur rohschnitt“ endet der Ablauf nach Schritt 2, das geht auch mit 16:9.
argument-hint: "<video> [nur rohschnitt] [notizen]"
allowed-tools: Bash, Read, Write, Edit, AskUserQuestion, Task
homepage: https://github.com/epictaste/claude-schnitt
repository: https://github.com/epictaste/claude-schnitt
author: epictaste
license: MIT
user-invocable: true
---

# /schnitt

Der Nutzer gibt dir ein Video, das er selbst gedreht hat: er spricht in die Kamera, sagt Sätze
mehrmals, verspricht sich, macht Pausen. Du gibst fertige Hochkant-Videos zurück, eins pro
Hook-Version. Du bist dabei der Cutter. Die Skripte messen, schneiden und rendern, die
Entscheidungen triffst du, und alles, was Geschmack ist, entscheidet der Nutzer.

Der Ablauf hat sechs Schritte. Jeder endet an einem Prüfpunkt, an dem der Nutzer „passt“ sagt,
bevor der nächste, teurere Schritt anfängt:

| Schritt | Was passiert | Prüfpunkt |
|---|---|---|
| 1 Voraussetzungen | Werkzeuge und Deepgram-Schlüssel prüfen, Projektordner anlegen | alles grün |
| 2 Rohschnitt | Transkript, beste Takes wählen, Kanten in die Stille legen | Take-Tabelle und Takes-Vorschau |
| 3 Stil beibringen | 2 bis 3 Referenzvideos ansehen, `stil.json` schreiben | Stilbeschreibung |
| 4 Stil testen | 3 Standbilder aus dem echten Video | „passt“ zu den Bildern |
| 5 Storyboard | Versionen schneiden, Gerüst bauen, Grafik-Optionen je Szene | Nutzer wählt je Szene |
| 6 Schnitt + Feinschliff | Licht, Augen, Zoom, Sounds, bauen, Endkontrolle | Abnahme grün, Vorschau angesehen |

Details zu jedem Schritt stehen in `referenz/schritt-N-*.md`. Lies die Datei des Schritts, bevor
du ihn anfängst. Das hier ist der Ablauf, dort stehen die Regeln.

## `SKILL_DIR` auflösen (vor jedem Befehl)

Jeder Befehl unten ruft ein Skript unter `SKILL_DIR/scripts/` auf. Setze `SKILL_DIR` auf den
**absoluten Pfad des Ordners, in dem DIESE SKILL.md liegt**, die du gerade gelesen hast. Den Pfad
hat dir das Read-Ergebnis gezeigt. Skripte, Vorlage und Referenz liegen immer direkt daneben:

```
Read ~/.claude/plugins/cache/epictaste/schnitt/<ver>/skills/schnitt/SKILL.md → SKILL_DIR=…/skills/schnitt
Read ~/.agents/skills/schnitt/SKILL.md                                       → SKILL_DIR=~/.agents/skills/schnitt
```

Setze den Pfad wörtlich ein und prüfe ihn einmal:

```bash
SKILL_DIR="<absoluter Pfad des Ordners mit der gelesenen SKILL.md>"
if [ ! -f "$SKILL_DIR/scripts/setup.py" ]; then
  echo "FEHLER: scripts/setup.py nicht gefunden unter SKILL_DIR=$SKILL_DIR" >&2
  exit 1
fi
PY="${SCHNITT_PYTHON:-$HOME/.config/schnitt/venv/bin/python}"   # legt setup.py an, mit numpy und pillow
```

Jedes Skript nennt mit `--help` seine Argumente. Weicht ein Aufruf hier davon ab, gilt `--help`.

## Grundregeln

1. **Das Video ist die Wahrheit.** Jeder Schnitt, jede Grafik und jeder Untertitel hängt an einem
   Wort, das wirklich gesprochen wurde, nachgeschlagen in den Wortzeiten. Keine geschätzten Zeiten.
   Ohne Deepgram-Schlüssel gibt es keine Wortzeiten, dann sag das klar und bau nichts aus geratenen Zeiten.
2. **Der Nutzer entscheidet über Geschmack.** Look, Grafik je Szene, Hook-Text, Licht und
   Zoom-Level schlägst du vor, mit Empfehlung, und er wählt. Fragen immer gebündelt in einem
   AskUserQuestion-Block mit 2 bis 4 Fragen, nie eine Frage pro Nachricht.
3. **Prüfen vor dem Teuren.** Rendern kostet Zeit und Token. Erst Tabelle, dann Vorschau, dann
   Standbilder, dann Render. Nie einen vollen Render starten, bevor die Standbilder abgenickt sind.
4. **Nichts erfinden.** Keine Zahl, kein Ergebnis und kein Logo, das es so nicht gibt. Fehlt ein
   Beispiel, fragen statt ausdenken.
5. **Der Skill verschickt nichts.** Er postet nicht, lädt nichts hoch, schreibt niemandem. Am Ende
   stehen Dateipfade, sonst nichts.
6. **Renders nie durch eine Pipe**, die früh schließt (`| head`). Remotion stirbt dann mitten im
   Lauf. Logs gehen in eine Datei.

## Projektordner

Alles zu einem Video liegt in einem Ordner im aktuellen Arbeitsverzeichnis:

```
schnitt-<videoname>/
├── rohschnitt/<videoname>/   deepgram.json woerter.json phrasen.md stille.json audio.wav schnitt.json kanten.json schnitt-hd.mp4
├── stil/         Referenz-Bilder, stil.md
├── schnitt/      bereiche.json meta.json woerter.json v*-neu.mp4 v*-hd.mp4 augen.json v*-cues.json grade.txt stil.json
├── remotion/     Kopie der Vorlage: src/reel.ts woerter.json augen.json stil.json szenen/ public/
└── aus/          fertige Videos, Abnahme-Berichte, Vorschauen
```

`audio.wav` ist die Fassung für die Spracherkennung (16 kHz). Sie ist **nie** der Ausgabe-Ton, der
kommt immer aus dem Originalvideo.

```bash
VIDEO="<absoluter Pfad zum Video>"
NAME="$(basename "${VIDEO%.*}" | tr '[:upper:] ' '[:lower:]-')"
P="$PWD/schnitt-$NAME"
R="$P/rohschnitt/$NAME"
mkdir -p "$P"/{stil,schnitt,remotion,aus} "$R"
```

**„nur rohschnitt“** in den Notizen heißt: Schritt 1 und 2, dann Ausgabe des Rohschnitts als MP4
im Format des Originals (auch 16:9), fertig. Keine Grafiken, keine Versionen.

## Schritt 1: Voraussetzungen

Details: `referenz/schritt-1-voraussetzungen.md`.

```bash
python3 "$SKILL_DIR/scripts/setup.py" --check
```

Exit 0: alles da, nichts sagen, weiter. Sonst `python3 "$SKILL_DIR/scripts/setup.py"` laufen
lassen (installiert ffmpeg und node über brew, legt die Python-Umgebung an, kompiliert das
Augen-Werkzeug, installiert die Vorlage) und bei fehlendem Schlüssel den Nutzer bitten, ihn in
`~/.config/schnitt/.env` einzutragen. Den Schlüssel nie selbst ausgeben oder ins Log schreiben.

Dann das Video ansehen: ein paar Frames ziehen und lesen (Format, Licht, wo die Person sitzt,
Hochkant oder quer). Hochkant ist für Schritt 3 bis 6 Pflicht.

## Schritt 2: Rohschnitt

Details und Take-Regeln: `referenz/schritt-2-rohschnitt.md`.

```bash
"$PY" "$SKILL_DIR/scripts/transkript.py" "$VIDEO" --out "$R"
```

`phrasen.md` komplett lesen, Take-Gruppen bilden, pro Gruppe den saubersten vollständigen Take
wählen (in der Regel den letzten). **Nur ganze, am Stück gesprochene Sätze**, nie Wörter aus der
Mitte eines Satzes schneiden, nie einen Satz aus zwei Takes kleben. `schnitt.json` schreiben.

Die Auswahl als Tabelle zeigen (Stelle, Zeit, behalten, raus, Grund), unsichere Stellen markieren,
rausgeworfene Hook-Sätze wörtlich zitieren. Erst nach dem OK weiter:

```bash
"$PY" "$SKILL_DIR/scripts/schnitt.py" kanten "$R" --pause-max 99 --pause-rest 99
"$PY" "$SKILL_DIR/scripts/straffen.py" "$R"
"$PY" "$SKILL_DIR/scripts/ausklang.py" "$R"
"$PY" "$SKILL_DIR/scripts/raeusper_check.py" "$R"
"$PY" "$SKILL_DIR/scripts/hd_take.py" "$R"
"$PY" "$SKILL_DIR/scripts/takes_vorschau.py" "$R" "$P/aus/takes-vorschau.mp4"
open "$P/aus/takes-vorschau.mp4"
```

`kanten` legt jede Kante in echte Stille und kürzt keine Pausen innerhalb eines Takes, nur zwischen
den Takes wird geschnitten. Jeder Treffer von `raeusper_check` wird behoben, bevor die Vorschau
rausgeht. Die Takes-Vorschau hört der Nutzer einmal komplett an, er findet Versprecher, die keine
Messung findet. **Kein Gerüst und keine Grafik, bevor er die Takes gehört hat.**

Bei „nur rohschnitt“ danach:
`"$PY" "$SKILL_DIR/scripts/schnitt.py" ausgabe "$R" --master --datei "$P/aus/rohschnitt.mp4"` und Pfad nennen.

## Schritt 3: Stil beibringen

Details: `referenz/schritt-3-stil-beibringen.md`, Standard-Look: `referenz/stil-standard.md`.

Frag nach 2 bis 3 Videos von Creatorn, deren Look der Nutzer mag (lokale Dateien). Die Referenzen
sollen sich ähneln, sonst mischst du die Stile.

```bash
"$PY" "$SKILL_DIR/scripts/stil_bilder.py" <referenz1> <referenz2> [<referenz3>] --aus "$P/stil"
```

Die Kontaktbögen lesen und beschreiben: Schrift, Farben, Hook-Text, Lage und Größe der Untertitel,
Schnitt-Tempo, Zooms, Grafiken. Daraus `$P/stil/stil.md` (Beschreibung in Worten) und
`$P/schnitt/stil.json` (Werte, Schema in `stil-standard.md`). Hat der Nutzer keine Referenzen oder
sagt „Standard“, gilt `stil-standard` unverändert. Die Beschreibung zeigen, „passt“ abwarten.

## Schritt 4: Stil testen

Details: `referenz/schritt-4-stil-testen.md`.

Vorlage ins Projekt kopieren, Stil einsetzen, drei Standbilder aus dem echten Video rendern:
Hook mit Plakat, Body weit, Body nah, alle mit Untertitel.

```bash
rsync -a --exclude node_modules --exclude out "$SKILL_DIR/template/" "$P/remotion/"
cp "$P/schnitt/stil.json" "$P/remotion/src/stil.json"
(cd "$P/remotion" && npm ci --no-audit --no-fund > "$P/aus/npm.log" 2>&1)
"$PY" "$SKILL_DIR/scripts/plakate.py" "$P/remotion" "$R/schnitt-hd.mp4" --aus "$P/aus/stilprobe" \
  --plakat "<Zeile 1>" "<Zeile 2>" --untertitel "<ein Satz aus dem Video>"
```

`plakate.py` zieht die Frames, rendert über die Komposition `Stilprobe` und legt die Bilder samt
Kontaktbogen `stilprobe-bogen.jpg` in `$P/aus/stilprobe/`. Lies alle drei selbst, bevor du sie zeigst: Untertitel nie im Gesicht, Plakat
nicht unter der Kopfzeile der Plattform, nichts am Rand. Erst wenn der Nutzer „passt“ sagt, geht es
weiter. Änderungen landen in `stil.json`, dann neue Standbilder.

## Schritt 5: Storyboard

Details: `referenz/schritt-5-storyboard.md`, Bau-Regeln: `referenz/regeln-grafiken.md`.

Versionen festlegen (welche Hook-Takes, welcher Body), dann schneiden, Ton holen, Wortzeiten je
Version holen:

```bash
"$PY" "$SKILL_DIR/scripts/versionen.py" "$R" "$P/schnitt" v1=1,2,4 v2=3,4 --body 5
"$PY" "$SKILL_DIR/scripts/ton_neu.py" "$R" "$P/schnitt"
"$PY" "$SKILL_DIR/scripts/dg_versionen.py" "$P/schnitt" <Fachwörter…>
```

Die Zahlen sind Clip-Nummern aus `kanten.json`. `dg_versionen` schreibt `schnitt/woerter.json`.
Leise Satzenden überhört die Spracherkennung manchmal: am Pegel prüfen, fehlende Wörter und
Hörfehler in `schnitt/woerter.json` von Hand korrigieren, bevor das Gerüst entsteht.

Dann das Storyboard. **Ein roter Faden:** ein Bild oder Objekt zieht sich durch alle
Vollbild-Szenen und erzählt Problem und Lösung. Pro Szene 2 bis 4 Optionen, jede in einer Zeile
(was man sieht, welcher Vorgang sich bewegt), Empfehlung mit ★. Echte Logos und bekannte Marken
statt Kästchen. Der Nutzer wählt, erst dann Code. Aus der Wahl entsteht `$P/spec.json`:

```bash
"$PY" "$SKILL_DIR/scripts/geruest.py" "$P/spec.json"
(cd "$P/remotion" && npx tsc --noEmit)
```

`geruest.py` schreibt `remotion/src/reel.ts`, `woerter.json`, `augen.json`, legt für jede Szene ohne
Datei einen sichtbaren Platzhalter `szenen/teil-<name>.tsx` an und schreibt die Szenen-Tabelle.

Szenen bauen: ein Agent für den roten Faden (alle Vollbild-Szenen aus einem Guss), ein zweiter für
die Szenen über dem Kopf. Kann dein Werkzeug keine Agents starten, baust du nacheinander selbst.
Jeder Agent bekommt `referenz/regeln-grafiken.md` als Brief, ausgefüllt mit Szenen, Wortlaut,
Marken und der gewählten Option. Stichproben der Standbilder selbst ansehen, nicht dem Bericht glauben.

## Schritt 6: Schnitt + Feinschliff

Details: `referenz/schritt-6-feinschliff.md`.

1. **Licht:** `"$PY" "$SKILL_DIR/scripts/licht.py" "$R/schnitt-hd.mp4" "$P/aus/licht" --zeit 20` zeigt
   5 Varianten am selben Frame mit gemessener Gesichtshelligkeit (`licht-bogen.jpg`). Der Nutzer wählt,
   `licht.py --waehle <1-5> --grade-datei "$P/schnitt/grade.txt"` schreibt die Wahl.
2. **HD-Takes und Augen:**
   `"$PY" "$SKILL_DIR/scripts/hd_take.py" "$R" --ziel "$P/schnitt"` baut aus `bereiche.json`
   je Version `v*-hd.mp4` mit dem Licht aus `grade.txt`, `"$PY" "$SKILL_DIR/scripts/augen_messen.py" "$P/schnitt"`
   misst die Augen je Clip. Danach `geruest.py` noch einmal, damit `augen.json` im Projekt landet,
   und die HD-Takes nach `remotion/public/video/` verlinken (`ln`, kein Symlink).
3. **Zoom je Version:** jede Version ein eigenes Level, Unterschied 0,05 bis 0,1, lieber etwas
   weiter raus. Standbild je Version zeigen, Nutzer bestätigt, Werte in `spec.json`.
4. **Sounds:** Cues aus den Szenen holen, dann mischen. `S2` ist der erste harte Schnitt in Sekunden:
   ```bash
   (cd "$P/remotion" && npm run -s cues -- v1 > "$P/schnitt/v1-cues.json")
   S2=$("$PY" -c "import json; print(json.load(open('$P/schnitt/meta.json'))['SATZ2']['v1'] / 30)")
   "$PY" "$SKILL_DIR/scripts/sfx_mix.py" "$P/schnitt/v1-neu.mp4" "$P/schnitt/v1-cues.json" "$S2" "$P/schnitt/v1-mix.wav"
   ```
   Alle Effekte gleich laut, rund 3 bis 4 dB unter der Stimme. Sounds sind die schwächste Stelle:
   der Nutzer hört sie selbst an.
5. **Bauen** (fortsetzbar, in Teilen, Ton aus der fertigen Mischung):
   ```bash
   zsh "$SKILL_DIR/scripts/bauen.sh" --projekt "$P/remotion" --komposition Reel-v1 \
     --ziel "$P/aus/v1.mp4" --ton-video "$P/schnitt/v1-mix.wav"
   ```
   Erst ein kurzes Stück mit `--frames 300` bauen und ansehen, dann das ganze Video (ohne `--frames`,
   mit `--neubau`, sonst passt der zwischengespeicherte Ton nicht). Der Master entsteht dabei über `master.sh`. Versionen
   nacheinander, nie zwei Renders gleichzeitig.
6. **Endkontrolle:** `"$PY" "$SKILL_DIR/scripts/abnahme.py" "$P/aus/v1.mp4" --take "$P/schnitt/v1-hd.mp4" --fix`.
   Technik (Lautheit, Spitzen, Farbtags) repariert `--fix`, alles Inhaltliche meldest du mit
   Zeitstempel. Kontaktbogen selbst lesen. Dann `zsh "$SKILL_DIR/scripts/vorschau.sh" "$P/aus/v1.mp4"`
   für eine 720p-Datei zum Ansehen auf dem Handy.

## Die erste Version ist ein Entwurf

Nach der ersten Vorschau kommt fast immer eine Runde Rückmeldung: eine Grafik anders, ein Untertitel
falsch geschrieben, ein Schnitt zu früh. Nimm sie als Liste mit Version und Zeitpunkt auf, ändere
nur das Genannte, rendere nur die betroffenen Teile neu (`bauen.sh` setzt fort) und zeig wieder die
Vorschau. Nichts nebenbei „verbessern“, was niemand angesprochen hat.

## Abnahme-Checkliste

- [ ] Takes-Vorschau angehört, Räusperer-Check ohne Treffer
- [ ] Stil abgenickt, drei Standbilder abgenickt
- [ ] Jede Grafik vom Nutzer gewählt, roter Faden erkennbar, echte Logos statt Kästchen
- [ ] Jede Szene hängt an Wortmarken, nichts geschätzt, keine Platzhalter mehr im Bild
- [ ] Untertitel nirgends im Gesicht, wechseln mit dem Schnitt, Hörfehler korrigiert
- [ ] Augen bei jedem Schnitt auf gleicher Höhe, jede Version eigenes Zoom-Level
- [ ] Sounds vom Nutzer angehört, Effekte unter der Stimme
- [ ] `npx tsc --noEmit` sauber, Abnahme grün oder gelbe Befunde gemeldet
- [ ] Kontaktbogen jeder Version selbst gelesen

## Fehlerbilder

| Symptom | Ursache | Lösung |
|---|---|---|
| Wort am Satzende fehlt im Schnitt | Kante lag auf der Wortzeit statt in der Stille | `ausklang.py` erneut, Ende bis in die Stille verlängern |
| Räusperer am Take-Anfang | Spracherkennung hängt ihn ans erste Wort | Clip-Start hinter die Stille legen, Ausschnitt gegentranskribieren |
| `marke(...)` wirft | Wort heißt im Transkript anders oder fällt in der Szene nicht | in `reel.ts` nachsehen, Schreibweise übernehmen |
| Video ohne Sound-Effekte | Remotion hat den Ton selbst gerendert | kein Audio-Element im Projekt, `--ton-video` mitgeben |
| Render stirbt ohne Fehler | Ausgabe in eine Pipe, die schloss | Log in Datei, `bauen.sh` macht das |
| Render bricht mit 404 ab | Video in `public/` ist ein Symlink | Hardlink mit `ln` statt `ln -s` |
| Kopf springt zwischen Schnitten | `augen.json` fehlt im Projekt | `augen_messen.py`, dann `geruest.py` erneut |
| Plattform meldet Duplikat | zwei Versionen mit gleichem Bild | jede Version eigenes Zoom-Level |

## Sicherheit

**Was der Skill tut:** ffmpeg, ffprobe und Remotion laufen lokal. Die Tonspur, und nur die, geht an
Deepgram (`api.deepgram.com`) für Wortzeiten. npm lädt beim ersten Projekt die Pakete und einen
Headless-Browser, beim Rendern kommen Schriften von Google Fonts. Er liest den Schlüssel aus
`~/.config/schnitt/.env` (Rückfall `~/.config/watch/.env`) und schreibt nur in den Projektordner.

**Was er nicht tut:** das Video hochladen, etwas posten oder versenden, den Schlüssel ausgeben.
Die Skripte liegen offen in `scripts/`, lies sie vor dem ersten Lauf, wenn du wissen willst, was sie tun.
