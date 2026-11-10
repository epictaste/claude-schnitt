# Stil: Standard

Der Look, wenn der Nutzer keine Referenzen mitbringt, und das Schema für `stil.json`.
Die Werte stehen in `template/src/stil.json`. Schritt 3 kopiert sie nach `schnitt/stil.json` und
ändert nur, was in den Referenzen zu sehen war.

## So sieht er aus

- **Hook:** Plakat in Gelb, Versalien, dunkle Kontur und kleiner Versatz-Schatten, zwei Zeilen,
  Oberkante bei y 470. Steht ab Frame 0 komplett, bis zum ersten harten Schnitt. Die Kamera zoomt
  dabei weich hinein, das Plakat spannt leicht mit.
- **Body:** die Person im Bild, der Zoom wechselt an jedem Take-Schnitt zwischen weit und nah, die
  Augen bleiben auf derselben Höhe. Grafiken über dem Kopf liegen auf einem weichen dunklen Hof,
  damit sie auf heller Wand tragen.
- **Vollbild:** dunkler Grund mit weichem Licht in der Mitte, Grafiken in warmem Weiß, ein Akzent.
- **Untertitel:** unter dem Kinn, höchstens zwei Wörter pro Bild, eine Zeile. Schlüsselwörter und
  lange Wörter stehen allein und größer in Versalien, jedes Wort kommt kurz aus der Unschärfe. Im
  Vollbild fest bei y 1500. Sie wechseln mit dem Schnitt, nichts steht über einen Schnitt hinweg.
- **Schrift:** Montserrat Black für das Plakat, Inter für Untertitel und Grafiken.
- **Sounds:** Riser über Satz 1, Whoosh auf dem ersten Schnitt, leise Klicks und Ticks auf
  sichtbaren Ereignissen, alle unter der Stimme.

## Schema `stil.json`

| Feld | Standard | Bedeutung |
|---|---|---|
| `name`, `beschreibung` | `standard` | wofür dieser Stil steht, in einem Satz |
| `schrift.plakat` | `Montserrat` | `Inter`, `Montserrat`, `Poppins` oder `Arimo` |
| `schrift.untertitel` | `Inter` | wie oben |
| `schrift.grafik` | `Inter` | wie oben |
| `farben.plakat` | `#FFD60A` | Farbe des Hook-Texts |
| `farben.plakatKontur` | `#111111` | Kontur um den Hook-Text und um Logos im Plakat |
| `farben.text` | `#F6F4F0` | Text in Grafiken und Untertiteln |
| `farben.textGedimmt` | `rgba(246,244,240,0.62)` | Nebentext, Labels |
| `farben.akzent` | `#FFD60A` | ein Akzent pro Szene |
| `farben.grund`, `farben.grundLicht` | `#0A0A0A`, `#2A2826` | Vollbild-Grund außen und in der Mitte |
| `farben.haken` | `#7CE3A0` | nur für Häkchen |
| `plakat.y` | `470` | Oberkante des Plakats in px, nie kleiner als 300 (darüber liegt die Kopfzeile der App) |
| `plakat.groesse` | `104` | größte Schriftgröße, lange Zeilen werden kleiner |
| `plakat.versalien` | `true` | Großbuchstaben |
| `plakat.kontur` | `3.2` | Dicke der Kontur in px |
| `plakat.maxBreite` | `940` | breiter wird keine Zeile |
| `untertitel.modus` | `springend` | `springend` (Größe je Wort) oder `einheitlich` (alle gleich groß) |
| `untertitel.groessen` | `[54, 68, 88, 108]` | Stufen s, m, l, xl im Modus `springend` |
| `untertitel.einheitlich` | `60` | Größe im Modus `einheitlich` |
| `untertitel.abstandKinn` | `25` | Abstand unter dem Kinn in px |
| `untertitel.vollbildY` | `1500` | Lage im Vollbild |
| `zoom.hookPlus` | `0.38` | so weit zoomt die Kamera über Satz 1 hinein |
| `zoom.nahPlus` | `0.1` | nah = weit plus dieser Wert |
| `zoom.augenZielY` | `990` | auf diese Höhe werden die Augen gelegt |
| `buehne` | `y 170, hoehe 600, maxBreite 900` | Grafikfläche über dem Kopf |
| `voll` | `x 70, y 260, breite 940, hoehe 1160` | Grafikfläche im Vollbild, endet über den Untertiteln |

Der Body-Zoom je Version steht in `spec.json` (`zoom`), weil er je Video und je Version anders ist.

## Was eine Referenz typischerweise ändert

| In der Referenz gesehen | Feld |
|---|---|
| Hook-Text weiß statt gelb, oder in Markenfarbe | `farben.plakat` |
| Hook-Text höher oder tiefer | `plakat.y` (nie kleiner als 300) |
| Untertitel alle gleich groß | `untertitel.modus: einheitlich`, `untertitel.einheitlich` |
| Untertitel weiter unten | `untertitel.abstandKinn` |
| ruhigere Kamera | `zoom.hookPlus` und `zoom.nahPlus` kleiner |
| andere Schriftanmutung | `schrift.*` auf die nächste der vier Familien |
| heller Grafik-Grund | `farben.grund`, `farben.grundLicht`, dazu `farben.text` dunkel |

Was die Vorlage nicht kann, wird in `stil/stil.md` als „nicht umgesetzt“ notiert. Wer es braucht,
baut es im Projekt in `Komposition.tsx` oder `Untertitel.tsx` nach, nach Rücksprache mit dem Nutzer.
