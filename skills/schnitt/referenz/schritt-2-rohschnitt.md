# Schritt 2: Rohschnitt

**Was ein Cutter hier macht:** Rohmaterial sichten, die besten Takes raussuchen, Versprecher, Räusperer und Leerlauf raus.
**Warum das Video es braucht:** Ein sauberer Rohschnitt ist die Hälfte des Videos. Jeder spätere Schritt baut darauf.

## 1. Transkript

```bash
"$PY" "$SKILL_DIR/scripts/transkript.py" "$VIDEO" --out "$R"
```

`$R` ist `$P/rohschnitt/<videoname>`, siehe Projektordner in SKILL.md. Alle Dateien dieses Schritts
liegen dort.

Holt die Wörter bei Deepgram (Füllwörter wie „äh“ bleiben sichtbar), speichert die Antwort
(ein zweiter Lauf kostet nichts, `--neu` erzwingt eine neue Abfrage), sucht alle stillen Stellen
und schreibt `phrasen.md`, eine Zeile pro Satz oder Satzstück:

```
P17 [02:14.30–02:17.80] (1.2s) ↻ P15, P16 · So, und jetzt zeig ich dir, wie das geht.
```

`(1.2s)` ist die Pause davor, `↻ P15, P16` heißt, dass die Phrase einer der vorherigen ähnelt. Das
ist nur ein Hinweis, Wiederholungen sind oft umformuliert. Jede Stelle selbst lesen. Bei mehr als
300 Phrasen in Blöcken lesen, getrennt an Pausen ab 2 s.

## 2. Takes wählen

`phrasen.md` komplett lesen, Take-Gruppen bilden. Regeln:

1. **Pro Gruppe gewinnt der letzte vollständige Take.** Wer wiederholt, wiederholt, bis es sitzt.
   Ausnahme: der letzte hat selbst einen Versprecher, bricht ab oder ist deutlich schwächer. Dann den
   besten davor nehmen und das im Grund sagen.
2. **Raus:** abgebrochene Ansätze, Kommentare an sich selbst („okay, nochmal“, „warte“),
   Füllwörter am Satzanfang mit Pause davor.
3. **Nur ganze, am Stück gesprochene Sätze.** Keine Einzelwort-Clips, kein Satz aus zwei Takes,
   nie Wörter aus der Mitte eines Satzes schneiden, um ihn schöner zu machen. Fehlt laut Transkript
   ein Satzanfang, den Ausschnitt mit 0,5 s Stille davor gegentranskribieren, bevor ein Wort von
   woanders dazukommt.
4. **Unklar, welcher Take besser ist?** Beide markieren und fragen. Nicht raten.
5. **Ein Satz, der nur einmal da ist, bleibt**, auch wenn er holpert. Der Rohschnitt erfindet nichts.
6. **Wort mit Konfidenz unter 0,8 an einer stillen Stelle** ist meist nicht gesprochen. Anderen Take nehmen.

`$R/schnitt.json` schreiben. `von` ist der Start des ersten behaltenen Wortes, `bis` das
Ende des letzten, in Sekunden aus `woerter.json`. Aufeinanderfolgende Phrasen zu einem Clip zusammenfassen:

```json
{
 "clips": [
  {"von": 0.0, "bis": 13.28, "phrasen": [1, 2, 3], "grund": "Intro, nur einmal gesprochen"},
  {"von": 21.04, "bis": 38.25, "phrasen": [7, 8], "grund": "dritter Take, die ersten zwei brechen ab"}
 ],
 "raus": [
  {"phrasen": [4, 5, 6], "grund": "zwei abgebrochene Ansätze und „okay nochmal“"}
 ]
}
```

## 3. Tabelle zeigen, erst dann schneiden

| Stelle | Zeit | behalten | raus | Grund |
|---|---|---|---|---|
| Hook | 00:00–00:13 | P4 | P1–P3 | P4 ist die letzte vollständige Version |

Dazu: Länge vorher und nachher, alle unsicheren Stellen. Wirfst du einen gesprochenen Hook-Satz
raus, den genauen Wortlaut zitieren, damit der Nutzer merkt, was fehlt. Erst nach dem OK weiter.
Sagt er „mach einfach“, weiter und die Tabelle trotzdem mitliefern.

## 4. Kanten in die Stille

```bash
"$PY" "$SKILL_DIR/scripts/schnitt.py" kanten "$R" --pause-max 99 --pause-rest 99
"$PY" "$SKILL_DIR/scripts/straffen.py" "$R"
"$PY" "$SKILL_DIR/scripts/ausklang.py" "$R"
"$PY" "$SKILL_DIR/scripts/raeusper_check.py" "$R"
```

- `kanten` schiebt jede Kante in echte Stille und sucht in beide Richtungen. Wortgrenzen der
  Spracherkennung liegen oft 100 bis 150 ms daneben, deshalb nie blind auf die Wortzeit schneiden.
  `--pause-max 99` heißt: Pausen innerhalb eines Takes bleiben, geschnitten wird nur zwischen Takes.
  Pausen in einem Take nur kürzen, wenn der Nutzer es sagt.
- **Exit 2** heißt: eine Kante hat keine Stille gefunden. Stelle in `phrasen.md` ansehen, Clip eine
  Phrase früher oder später enden lassen oder fragen. Nie ignorieren, dort wird ein Wort angeschnitten.
- `straffen` zieht die Ränder an die Sprache, `ausklang` verlängert Enden wieder, wenn ein leiser
  Endkonsonant (t, s, f) sonst gekappt wäre.
- `raeusper_check` sucht das Muster „kurzer lauter Block, Stille, dann Satz“ an Clip-Anfängen und
  -Enden. Jeder Treffer: Clip-Start hinter die Stille legen (1 Frame Luft), dann `kanten` neu.

Prüfen, was keine Messung findet:
- In den ersten 2 s jedes Clips jedes Wort über 0,6 s im Pegel ansehen. Fehlstarts („Claude, ähm …
  Mods sind neu“) verstecken sich in einem gedehnten Wort.
- Fehlt ein Wort aus dem Skript, den Ausschnitt einzeln mit dem Wort als Fachbegriff transkribieren.

## 5. Takes-Vorschau

```bash
"$PY" "$SKILL_DIR/scripts/hd_take.py" "$R"
"$PY" "$SKILL_DIR/scripts/takes_vorschau.py" "$R" "$P/aus/takes-vorschau.mp4"
open "$P/aus/takes-vorschau.mp4"
```

`hd_take.py` schneidet nur die gewählten Stellen aus dem Original (iPhone-HDR wird nach SDR
umgerechnet) und klebt sie zu `$R/schnitt-hd.mp4`. Bei einem 4K-Video dauert das ein paar Minuten.
Die Vorschau zeigt alle gewählten Takes hintereinander, Ton aus dem Original, 720p. Der Nutzer hört einmal drüber und
nennt Versprecher. Erst danach geht es weiter, vorher wird nichts gebaut.

## Nur Rohschnitt

```bash
"$PY" "$SKILL_DIR/scripts/schnitt.py" ausgabe "$R" --master --datei "$P/aus/rohschnitt.mp4"
```

Schreibt den fertigen Rohschnitt im Format des Originals (auch 16:9) nach `$P/aus/rohschnitt.mp4`,
Bildanzahl geprüft. Ohne `--master` entsteht eine 720p-Vorschau. Bei 4K-Material dauert beides
mehrere Minuten, weil das ganze Original dekodiert wird: im Hintergrund laufen lassen, Log in eine Datei. Pfad nennen, fertig.

**Prüfpunkt:** Tabelle abgenickt, Vorschau angehört, Räusperer-Check ohne offenen Treffer.
