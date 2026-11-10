# Schritt 3: Stil beibringen

**Was ein Cutter hier macht:** sich vom Kunden zeigen lassen, was ihm gefällt, und daraus einen Look ableiten.
**Warum das Video es braucht:** Ohne Vorgabe baut Claude einen Durchschnittslook. Mit zwei, drei Beispielen trifft es deinen.

## Referenzen holen

Frag nach 2 bis 3 Videos von Creatorn, deren Look der Nutzer übernehmen will, als lokale Dateien.
Der Skill lädt nichts aus dem Netz. Hat der Nutzer nur Links, lädt er die Videos selbst herunter.

Die Referenzen sollen sich ähneln (gleiches Format, ähnlicher Look). Drei völlig verschiedene Videos
ergeben einen Mischmasch. Ist eins deutlich anders, frag, welches gewinnt.

## Ansehen

```bash
"$PY" "$SKILL_DIR/scripts/stil_bilder.py" <referenz1> <referenz2> [<referenz3>] --aus "$P/stil"
```

Zieht je Video 6 Frames über die Länge verteilt und legt einen Kontaktbogen je Video an. Lies jeden
Bogen und, wenn nötig, einzelne Frames in voller Größe. Wer das Transkript einer Referenz braucht
(Tempo, wie oft geschnitten wird), lässt `transkript.py` darauf laufen. Das kostet Deepgram-Guthaben,
also nur auf Nachfrage.

## Beschreiben

Halte für jede Referenz fest, was du siehst, nicht was du vermutest:

| Merkmal | Worauf achten |
|---|---|
| Hook-Text | Lage (Oberkante in px), Farbe, Kontur oder Box, Versalien, Zeilen, wie lange er steht |
| Schrift | Familie (am nächsten: Inter, Montserrat, Poppins, Arimo), Gewicht |
| Untertitel | Lage (unter dem Kinn, Mitte, unten), Wörter pro Bild, Größe, Farbe, Schlüsselwörter größer |
| Farben | Grund der Grafiken, Text, ein Akzent |
| Schnitt-Tempo | wie oft ein Schnitt, ob Zoom-Sprünge auf Schnitten |
| Zoom | weit/nah im Wechsel, wie stark |
| Grafiken | über dem Kopf oder Vollbild, Karten oder freie Objekte, Logos |

## Festhalten

1. `$P/stil/stil.md`: der Look in Worten, eine Zeile pro Merkmal, mit Verweis auf das Bild, aus dem
   es kommt. Gemeinsamkeiten der Referenzen zuerst, Abweichungen danach.
2. `$P/schnitt/stil.json`: die Werte. Schema und Standardwerte stehen in `stil-standard.md`. Nur
   Felder ändern, die du in den Referenzen gesehen hast. Alles andere bleibt Standard.

Grenzen der Vorlage offen sagen: Schriften gibt es in der Vorlage vier, ein exotischer Font wird auf
den nächsten gemappt. Was die Vorlage nicht kann (Untertitel mit Box, Text hinter der Person),
steht als „nicht umgesetzt“ in `stil.md`, statt still weggelassen zu werden.

## Ohne Referenzen

Sagt der Nutzer „Standard“ oder hat keine Referenzen, `stil-standard` übernehmen:

```bash
cp "$SKILL_DIR/template/src/stil.json" "$P/schnitt/stil.json"
```

**Prüfpunkt:** Beschreibung gezeigt, Nutzer sagt „passt“. Design-Entscheidungen nie selbst treffen
und ausrollen: Farben und Look schlägst du vor, er wählt.
