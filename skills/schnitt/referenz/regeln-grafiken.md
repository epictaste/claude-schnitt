# Regeln für Grafiken (Brief für Bau-Agents)

Diese Datei ist der Brief für jeden, der Szenen baut, ob Agent oder du selbst. Oben ausfüllen, den
Rest wörtlich mitgeben. Die Regeln sind keine Geschmacksfragen, jede steht hier, weil ihr Fehlen ein
Video sichtbar schlechter gemacht hat.

## Auftrag (ausfüllen)

```
Projekt:     <$P>/remotion
Szenen:      <name> (<von>-<bis> Body-Frames, Vollbild ja/nein), …
Datei je Szene: src/szenen/teil-<name>.tsx, Exporte <Name>Szene und <Name>Cues
Gesprochen:  <Wortlaut je Szene, aus dem Kommentar in reel.ts>
Gewählt:     <die Option, die der Nutzer je Szene gewählt hat, in einer Zeile>
Roter Faden: <das Objekt, das sich durch alle Vollbild-Szenen zieht, und wo es gemeinsam liegt>
Logos:       <Dateien in public/logos/, die genutzt werden dürfen>
Farben:      <über stil.json hinaus erlaubt, z. B. Markenfarben einer App>
Frame-Start: Szene <name> beginnt im Video bei Frame <HOOK[v1] + von> (für Standbilder)
```

Nur die genannten Dateien anfassen. `reel.ts`, `stil.json`, `Komposition.tsx`, `Untertitel.tsx`,
`bausteine.tsx` und `szenen/index.ts` gehören dir nicht. Bausteine importieren, nicht kopieren.
Frame 0 in einer Szene ist der Szenenstart.

## Regeln

**1. Das Video ist die Wahrheit.** Jeder Wechsel liegt auf einem gesprochenen Wort:
`marke(m, 'wort')` aus `geteilt.tsx`. Frames nie selbst rechnen oder schätzen. Die Schreibweise der
Marken steht im Kommentar und in `m` in `reel.ts`, nicht im Skript des Sprechers.

**2. Bildaufbau.** Zwei Arten von Szenen:
- *Über dem Kopf:* Person im Bild, Grafik in `<Buehne>` (Fläche über dem Kopf, mittig, höchstens
  `STIL.buehne.maxBreite` breit). Nichts unterhalb der Bühne, darunter liegen Kopf und Untertitel.
- *Vollbild:* keine Person, dunkler Grund kommt von der Komposition. Inhalt in `<Voll>`, nichts
  darunter, dort stehen die Untertitel.
Plakat und Untertitel baut die Komposition, nie eine Szene.

**3. Keine leere Hülle.** Karte und ihr erster Inhalt erscheinen im selben Frame. Eine leere Box,
die steht, während der Inhalt noch eintröpfelt, liest sich als Stillstand.

**4. Vorgang statt Text.** Jede Szene zeigt einen Vorgang, den man sieht: etwas wandert, wird
gegriffen, füllt sich, leuchtet auf, wird weggewischt. Höchstens 5 Wörter gleichzeitig im Bild,
nichts unter 32 px (auf dem Handy unlesbar). Code-Zeilen nur, wenn genau die Zeile der Vorgang ist.

**5. Bekannte Dinge, echte Beispiele.** Echte Logos aus `public/logos/` (`<Logo>`), echte
Oberflächen, Alltagsgegenstände. Dateien als erkennbare Icons nach Typ (`<DateiIcon>`: PDF, Folie,
Tabelle, Text, Bild, Video, Mail, Ordner), nie als neutrale Kästchen. Keine Platzhalter-Balken,
keine Chips wie „dein Fall“. Fehlt ein Beispiel im Auftrag, nachfragen statt ausdenken.

**6. Der rote Faden.** Das Objekt aus dem Auftrag ist in allen Vollbild-Szenen dasselbe, als
gemeinsame Komponente in einer eigenen Datei (z. B. `src/szenen/raster.tsx`). Es verändert sich
mit der Geschichte, es wird nicht in jeder Szene neu erfunden.

**7. Deckung.** Gesagte Zahl gleich gezeigte Zahl: wer „zehnmal“ sagt, bekommt 10 ins Bild, nicht
9,4. Wo nur gezählt wird („drei Agenten, einer plant, einer baut, einer prüft“), benennt die Grafik
(Planer, Umsetzer, Prüfer), nie eine nackte 1, 2, 3. Keine Quellen-Anhängsel im Bild. Kein Text,
der wiederholt, was gesagt wird.

**8. Namen.** Wird ein Produkt oder Tool genannt, steht es groß im Bild, als Logo und Name.

**9. Standzeit und Bewegung.**
- Jedes Textelement steht mindestens 25 Frames bis zum nächsten Szenenwechsel. Schafft es das
  nicht, gehört es nicht ins Bild. Keine nachgeschobene Erklärzeile kurz vor Szenenende.
- Eine fertig aufgebaute Grafik steht danach höchstens rund 15 Frames still. Ist der Satz länger,
  kommt ein weiterer Schritt: nächste Zeile, ein Wert fällt, ein Häkchen, ein Strich, ein Zoom auf
  ein Detail. Über 20 Frames ganz ohne Bewegung ist ein Befund.
- Tempo schlägt wörtliche Deckung: die Grafik muss nicht exakt bebildern, was in dem Moment gesagt
  wird, sie muss in Bewegung bleiben. Regel 7 gilt trotzdem, was gezeigt wird, stimmt.

**10. Keine leere Zone.** Die Grafikfläche ist nie länger als 10 Frames leer, auch nicht am Anfang
einer Szene. Ab Frame 0 jeder Szene ist etwas zu sehen. Beginnt eine Szene mit einem Satz ohne
eigenes Bild, hält die letzte Szene sichtbar hinein oder das Ausgangsbild steht schon da.

**11. Bewegungsart.** Erscheinen über `<Scharf>` (aus der Unschärfe), gezeichnete Linien und Pfeile
(`<Pfeil>`, die Spitze erst ab 85 % der Strecke), Tippen, Balken, die sich füllen, Dinge, die
einrasten (`einrasten()`). Kein Einblenden über Deckkraft allein, nichts schwebt ziellos.

**12. Farbe und Schrift.** Nur `FARBE` und `GRAFIK_FONT` aus `bausteine.tsx`, die Werte kommen aus
`stil.json`. Ein Akzent pro Szene. Grün nur für Häkchen. Grau nur in nachgebauten Oberflächen.
Erlaubt darüber hinaus: Markenfarben einer gezeigten App und die Typfarben von Datei-Icons, wenn der
Auftrag sie nennt. Flächen bleiben dunkel, Farbe ist Akzent.

**13. Text.** Deutsch (oder die Sprache des Videos), echte Umlaute, keine Gedankenstriche, Namen
richtig geschrieben (Claude, nicht Cloud). `whiteSpace: 'nowrap'` für Beschriftungen, Breite prüfen.

**14. Geheimes verpixeln.** Ganze Prompts, Schlüssel, private Pfade, fremde Namen kommen unter
`<Mosaik>`, die erste Zeile darf lesbar bleiben.

**15. Sounds.** `<Name>Cues(m, dauer)` gibt `{frame, sound}` relativ zur Szene zurück, `sound` ist
`click`, `tick`, `pop`, `whoosh` oder `type` (`tippTicks()` für Tippen). Ein Sound pro sichtbarem
Ereignis, nicht für jede Kleinigkeit. Keine Lautstärke angeben, die setzt die Mischung einheitlich.
**Kein Audio-Element im Projekt**, auch nicht im Kommentar: sonst ignoriert der Bau die Mischung.

## Selbsttest vor dem Melden

1. `npx tsc --noEmit` im Projekt, sauber.
2. Je Szene mindestens 4 Standbilder rendern und mit Read ansehen: Anfang, Mitte, ein
   Zwischenstand einer Bewegung, Ende.
   ```bash
   npx remotion still Zone-v1 out/<szene>-f<N>.png --frame=<N>
   ```
3. Für jede Textzeile die Standzeit ausrechnen, die längste Standphase je Szene nennen.
4. Abgeschnittener Text, gesprengte Karte, leerer Frame, Text unter 32 px, eine Zeile unter
   25 Frames Standzeit: beheben, bevor du meldest.

Optional für die leere Zone (Regel 10) über ein fertig gebautes Video:

```bash
ffmpeg -v error -i <video>.mp4 -vf "crop=1080:840:0:0,scale=54:42" -pix_fmt gray -f rawvideo - | python3 -c "
import sys
b = sys.stdin.buffer.read(); n = 54 * 42; vorher = None
for i in range(len(b) // n):
    f = b[i*n:(i+1)*n]; m = sum(f) / n
    std = (sum((x - m) ** 2 for x in f) / n) ** 0.5
    diff = 0 if vorher is None else sum(abs(x - y) for x, y in zip(f, vorher)) / n
    print(i, round(std, 1), round(diff, 1)); vorher = f
"
```

Standardabweichung unter 4 heißt leer, 4 bis 8 eine dunkle Karte, die beim Scrollen wie leer wirkt.
Phasen über 10 Frames darunter oder ohne Bewegung auflisten und beheben oder melden.

## Bericht

Je Szene: Datei, was der Vorgang ist, an welchen Marken er hängt, Pfade der Standbilder, längste
Standphase, offene Fragen. Keine Erfolgsmeldung ohne angesehene Standbilder.
