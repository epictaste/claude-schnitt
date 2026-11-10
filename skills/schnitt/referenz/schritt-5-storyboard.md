# Schritt 5: Storyboard

**Was ein Cutter hier macht:** pro Satz festlegen, was im Bild passiert.
**Warum das Video es braucht:** Grafiken, die eine Geschichte erzählen, halten Zuschauer. Einzelbilder ohne Zusammenhang nicht.

## 1. Versionen

Wurden mehrere Hooks hintereinander gesprochen, entsteht je Hook eine Version mit demselben Body.
Frag gebündelt: welche Hooks, welche Versionen, wo der Body beginnt. Die Zahlen sind Clip-Nummern
aus `$R/kanten.json` (1 = erster Clip):

```bash
"$PY" "$SKILL_DIR/scripts/versionen.py" "$R" "$P/schnitt" v1=1,2,4 v2=3,4 v3=5,4 --body 6
"$PY" "$SKILL_DIR/scripts/ton_neu.py" "$R" "$P/schnitt"
"$PY" "$SKILL_DIR/scripts/dg_versionen.py" "$P/schnitt" <Fachwörter, die oft falsch erkannt werden>
```

- `versionen.py` schreibt `bereiche.json` und `meta.json` (`HOOK`, `SATZ2`, `TAKE_SCHNITTE`, `BODY`).
- `ton_neu.py` schneidet den Ton je Version direkt aus dem Original (48 kHz) nach `v*-neu.mp4`.
- `dg_versionen.py` holt die Wortzeiten je Version neu und schreibt `schnitt/woerter.json`
  (`hook.v1`, `hook.v2`, …, `body`).

Danach `schnitt/woerter.json` lesen und gegen das Gesprochene halten. Leise Satzenden überhört die
Spracherkennung: Pegel nach dem Wort prüfen, ist dort Sprache, das Wort von Hand nachtragen.
Hörfehler (ein Produktname als ähnliches Alltagswort) dort korrigieren. Untertitel-Korrekturen,
die nur die Anzeige betreffen, gehören in `remotion/src/korrektur.json`.

## 2. Roter Faden

Ein Bild oder Objekt zieht sich durch alle Vollbild-Szenen und erzählt Problem und Lösung. Beispiele:
- ein Raster aus Datei-Icons, durch das Claude im Zickzack springt, bis eine Karte sie verbindet
- ein Trichter, in den Bewerbungen fallen, und ein Filter, der aussiebt
- eine Timeline, auf der Clips von selbst an ihren Platz rutschen

Einfach wie ein Diagramm, bekannte Dinge, zeigen wie es passiert. Keine Wand aus Log-Zeilen, keine
verspielten Figuren-Metaphern. Schlag 2 bis 3 rote Fäden vor, der Nutzer wählt einen.

## 3. Szenen und Optionen

Teile den Body in Szenen, jede Grenze auf einem Take-Schnitt (`TAKE_SCHNITTE` minus `HOOK`).
Für jede Szene 2 bis 4 Optionen, jede in einer Zeile: was man sieht und welcher Vorgang sich bewegt.
Empfehlung mit ★. Zwei harte Regeln für jede Option:

1. **Bekannte Dinge.** Echtes Logo, echte Oberfläche, Alltagsgegenstand (Ordner, Schlüssel, Blatt
   Papier, Ampel). Dateien als erkennbare Icons nach Typ, nie als neutrale Kästchen.
2. **Vorgang statt Text.** Jede Szene zeigt einen Vorgang: etwas wandert, füllt sich, leuchtet auf,
   wird weggewischt. Höchstens 5 Wörter im Bild, der Rest gehört in den Sprechtext.

Je Szene festlegen: **Vollbild** (nur Grafik, ohne Person, Untertitel unten fest) oder **über dem
Kopf** (Person bleibt im Bild, Grafik auf der Fläche darüber). Vollbild trägt den roten Faden,
über dem Kopf stehen kurze Stücke wie ein Logo, eine Zahl, das Kommentar-Wort.

Bei mehr als 4 Szenen in mehreren gebündelten Blöcken fragen. Nie direkt losbauen. Fehlt ein
Beispiel (welches Logo, welche Zahl), fragen statt ausdenken.

## 4. spec.json und Gerüst

Aus der Wahl entsteht `$P/spec.json`:

```json
{
 "titel": "Claude schneidet mein Video",
 "augen_y": 1000, "kopf_y": 860, "gesicht_x": 540,
 "zoom": {"v1": 1.1, "v2": 1.04, "v3": 1.16},
 "plakat": {"v1": ["Claude schneidet", "mein Video"], "v2": ["[logo:app.png] am Mac"], "v3": ["Nie mehr", "selbst schneiden"]},
 "hook_szene": {"v2": "raster"},
 "body": [["intro", 0, 110, false], ["raster", 110, 325, true], ["karte", 325, 528, true], ["cta", 528, 640, false]]
}
```

- `kopf_y` ist die Kopf-Oberkante, `augen_y` und `gesicht_x` grob aus einem Frame. Genau misst
  `augen_messen.py` in Schritt 6, dann gilt `augen.json`.
- `zoom` je Version verschieden, siehe Schritt 6. Vorläufige Werte reichen hier.
- `hook_szene` ist optional: eine Vollbild-Szene von `SATZ2` bis zum Hook-Ende. Endet der Hook mit
  Satz 1, fällt sie weg.
- `body`: `[name, von, bis, vollbild]` in Body-Frames. Namen nur Kleinbuchstaben, Ziffern, Bindestrich.

```bash
"$PY" "$SKILL_DIR/scripts/geruest.py" "$P/spec.json"
(cd "$P/remotion" && npx tsc --noEmit)
```

`geruest.py` schreibt `remotion/src/reel.ts` (Versionen, Wortzeiten, Szenen mit Marken),
`woerter.json`, `augen.json` und `szenen/index.ts`. Für jede Szene ohne Datei legt es einen
Platzhalter an, der seinen Namen groß zeigt. `szenen/teil-beispiel.tsx` aus der Vorlage löschen,
wenn das Projekt es nicht nutzt. `reel.ts` nie von Hand ändern, sondern `spec.json` und neu laufen lassen.

**Marken:** jede Szene bekommt `m`, den Startframe jedes Wortes relativ zum Szenenstart.
Schlüssel klein, Umlaute als ae/oe/ue/ss, Zahlen mit `n` davor, doppelte Wörter mit 2, 3 dahinter.
Im Code `marke(m, 'karte')` statt einer Zahl.

## 5. Szenen bauen

Ein Agent für den roten Faden (gemeinsame Komponente plus alle Vollbild-Szenen), ein zweiter für die
Szenen über dem Kopf. Jeder bekommt den Brief aus `regeln-grafiken.md`, ausgefüllt. Ohne Agents
baust du selbst, eine Szene nach der anderen, mit denselben Regeln.

Jede Szendatei exportiert `<Name>Szene` (Komponente, Props `m`, `dauer`, `version`) und
`<Name>Cues` (Sounds, Frames relativ zur Szene). Der Name ist der Szenenname in PascalCase,
`schneiden-am-mac` wird `SchneidenAmMac`.

Standbilder ohne Video (schnell):

```bash
cd "$P/remotion" && npx remotion still Zone-v1 out/<szene>-f<N>.png --frame=<N>
```

`<N>` ist der Frame im ganzen Video: `HOOK[v1]` plus Szenen-`von` plus Frame in der Szene.

Den Bericht eines Agents nicht ungeprüft übernehmen: selbst ein paar Standbilder lesen, besonders
Anfang und Ende jeder Szene.

**Prüfpunkt:** jede Szene gewählt und gebaut, keine Platzhalter mehr, `npx tsc --noEmit` sauber.
