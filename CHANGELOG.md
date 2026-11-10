# Änderungen

Alle wichtigen Änderungen an `/schnitt`, vorher `/cut`.

## [2.0.0] 2026-11-10

Neu aufgebaut und umbenannt. **`/schnitt` ersetzt `/cut`**, das Repo heißt jetzt `claude-schnitt`.
Wer `/cut` installiert hat, deinstalliert es und installiert `schnitt@epictaste`.

### Neu
- **Sechs Schritte mit Prüfpunkten:** Voraussetzungen, Rohschnitt, Stil beibringen, Stil testen,
  Storyboard, Schnitt und Feinschliff. Jeder Schritt hat ein eigenes Dokument in `referenz/`.
- **Rohschnitt:** Transkript mit Wortzeiten, Claude wählt die besten Takes nach festen Regeln (nur
  ganze Sätze, der letzte vollständige Take gewinnt, unklare Stellen werden gefragt), Kanten werden
  in echte Stille gelegt, Räusperer an Take-Anfängen gesucht, Takes-Vorschau zum Anhören.
  `nur rohschnitt` hört danach auf und geht auch mit Querformat.
- **Stil aus Referenzvideos:** 2 bis 3 Videos von Creatorn werden als Kontaktbögen angesehen und in
  `stil.json` und `stil.md` übersetzt. Ohne Referenzen gilt ein Standard-Look.
- **Stilprobe:** drei Standbilder aus dem echten Video (Hook mit Plakat, Body weit, Body nah), bevor
  gerendert wird.
- **Storyboard mit rotem Faden:** je Szene 2 bis 4 Optionen, der Nutzer wählt. `geruest.py` schreibt
  `reel.ts` mit Versionen, Wortzeiten und Wortmarken je Szene und legt Platzhalter für neue Szenen an.
- **Feinschliff:** fünf Licht-Varianten mit gemessener Gesichtshelligkeit, Augen je Clip gemessen
  und auf gleiche Höhe gelegt, Zoom-Wechsel auf jedem Take-Schnitt, eigenes Zoom-Level je Version,
  wortgenaue Untertitel, die mit dem Schnitt wechseln.
- **Bauen in Teilen**, fortsetzbar nach einem Abbruch, Ton aus der fertigen Mischung.
- **Endkontrolle:** Lautheit, Spitzen, Farbtags, Tonlöcher, eingefrorene und falsche Frames,
  Helligkeitssprünge, Sync. Technik repariert sie selbst, Inhaltliches meldet sie.
- **iPhone-HDR:** HLG wird über eine eigene LUT (`assets/hlg709.cube`, erzeugt von `scripts/hlg_lut.py`)
  nach BT.709 umgerechnet, nur die gewählten Stellen, nicht das ganze 4K-Video.
- **Vorlage:** Kompositionen `Reel-<v>`, `Zone-<v>` und `Stilprobe`, Bausteine für Szenen (echte
  Logos, Datei-Icons nach Typ, Pfeile, Häkchen, Mosaik), Cue-Export für die Sounds.

### Entfernt
- Die Animationszone über dem Kopf mit harter Kante aus 1.x, `words.py`, `zone.py`, `cut.py`,
  `build.py` und `PART_BRIEF.md`. Ihre Aufgaben übernehmen die sechs Schritte.

## [1.0.1] 2026-09-13

Letzte Version von `/cut`: eigene Teilfolge je Version, Bildraten-Prüfung, Abbruch bei
abweichender Bildanzahl.

## [1.0.0] 2026-09-13

Erste Version von `/cut`.
