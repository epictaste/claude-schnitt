# Schritt 4: Stil testen

**Was ein Cutter hier macht:** dem Kunden ein paar Standbilder zeigen, bevor er stundenlang rendert.
**Warum das Video es braucht:** Ein Standbild kostet Sekunden, ein falscher Render Stunden und viele Token.

## Projekt anlegen

```bash
rsync -a --exclude node_modules --exclude out "$SKILL_DIR/template/" "$P/remotion/"
cp "$P/schnitt/stil.json" "$P/remotion/src/stil.json"
(cd "$P/remotion" && npm ci --no-audit --no-fund > "$P/aus/npm.log" 2>&1)
(cd "$P/remotion" && npx tsc --noEmit)
```

Ohne `rsync`: `cp -R "$SKILL_DIR/template/." "$P/remotion/"` und danach `node_modules` und `out`
im Projekt löschen, falls mitkopiert. Das Projekt hat sein eigenes `public/`. Nie auf einen großen,
geteilten Ordner zeigen, Remotion kopiert `public/` bei jedem Render.

Logos, die im Video vorkommen, legt der Nutzer nach `$P/remotion/public/logos/` (siehe `LIESMICH.md`
dort). Auf dem Mac geht das Icon einer App auch per `sips` aus dem Programmpaket.

## Drei Standbilder

```bash
"$PY" "$SKILL_DIR/scripts/plakate.py" "$P/remotion" "$R/schnitt-hd.mp4" --aus "$P/aus/stilprobe" \
  --plakat "<Zeile 1>" "<Zeile 2>" --untertitel "<ein Satz aus dem Video>" \
  [--hook-zeit 1.0] [--body-zeit 8.0] [--zoom 1.1] [--augen-y 1000] [--gesicht-x 540]
```

`plakate.py` zieht zwei Frames aus dem Rohschnitt (`--hook-zeit`, `--body-zeit`, Sekunden in
`schnitt-hd.mp4`) nach `remotion/public/stilprobe/` und rendert über die Komposition `Stilprobe` drei
Bilder plus Kontaktbogen `stilprobe-bogen.jpg` nach `$P/aus/stilprobe/`:

| Bild | Inhalt |
|---|---|
| Hook | Frame aus Satz 1, Plakat mit Hook-Text, Zoom wie am Ende des Hook-Zooms, Untertitel |
| Body weit | Frame aus dem Body (gern mit ausgestreckten Armen), weiter Zoom, Untertitel |
| Body nah | gleicher Frame, naher Zoom, Untertitel |

Die Komposition `Stilprobe` nimmt diese Props (für Einzelbilder auch direkt nutzbar):

```bash
cd "$P/remotion" && npx remotion still Stilprobe out/probe.png \
  --props='{"bild":"stilprobe/body.png","modus":"nah","plakat":[],"untertitel":"die besten Takes","zoom":1.1,"augenY":1000,"gesichtX":540}'
```

`modus` ist `plakat`, `weit` oder `nah`. `plakat` ist eine Liste von Zeilen, ein Logo kommt als
`[logo:datei.png]` in die Zeile. `augenY` und `gesichtX` sind die Augenhöhe und die Gesichtsmitte im
Frame (grob ablesen, genau misst es erst Schritt 6).

## Selbst prüfen, dann zeigen

Lies jedes Bild, bevor der Nutzer es sieht:
- Untertitel nie im Gesicht, vollständig sichtbar, nicht unter der Bedienleiste der Plattform.
- Plakat-Oberkante nicht über y 300, sonst liegt es unter der Kopfzeile der App.
- Arme im weiten Bild noch drauf, im nahen Bild der Kopf nicht angeschnitten.
- Nichts klebt am Rand, kein Text abgeschnitten.

Dann alle drei zeigen und gebündelt fragen: Hook-Text, Zoom, Untertitel-Lage, Farben. Änderungen
gehen in `schnitt/stil.json` (und die Kopie in `remotion/src/stil.json`), dann neue Bilder.

**Prüfpunkt:** Nutzer sagt „passt“ zu den drei Bildern. Erst danach Schritt 5.
