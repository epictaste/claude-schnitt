# /schnitt

**Claude schneidet dein Video.**

Du drehst, Claude schneidet: die besten Takes raus, Versprecher und Räusperer weg, ein Look nach
deinen Vorbildern, Grafiken, die du auswählst, Untertitel Wort für Wort, Zoom auf jedem Schnitt,
Augen bei jedem Schnitt auf derselben Höhe, Sounds, mehrere Hook-Versionen und eine Endkontrolle,
bevor du irgendwas postest.

```
/plugin marketplace add epictaste/claude-schnitt
/plugin install schnitt@epictaste
/schnitt dein-video.mov
```

> **Version 2.0 ersetzt `/cut`.** Das Repo hieß vorher `claude-cut`. Wer `/cut` installiert hat,
> deinstalliert es (`/plugin uninstall cut@epictaste`) und installiert `schnitt` wie oben.

## Für wen

Für alle, die vor der Kamera sprechen und nicht stundenlang im Schnittprogramm sitzen wollen.
Programmieren musst du nicht. Du redest mit Claude, Claude ruft die Werkzeuge auf.

Gebaut für den **Mac**. Auf anderen Systemen laufen die meisten Schritte, die Augen-Messung nicht.

## Die sechs Schritte

| Schritt | Was ein Cutter sonst macht | Was Claude macht | Was du machst |
|---|---|---|---|
| 1 Voraussetzungen | Arbeitsplatz einrichten | prüft und installiert ffmpeg, Node und Remotion | Deepgram-Schlüssel eintragen |
| 2 Rohschnitt | Material sichten, beste Takes wählen | liest das Wort-Transkript, findet doppelte und verpatzte Takes, legt jeden Schnitt in die Stille | Take-Tabelle abnicken, Takes-Vorschau anhören |
| 3 Stil beibringen | sich zeigen lassen, was gefällt | schaut 2 bis 3 Videos von Creatorn an, deren Look du magst, und beschreibt Schrift, Farben, Untertitel, Tempo | „passt“ sagen |
| 4 Stil testen | Standbilder zeigen, bevor gerendert wird | baut 3 Standbilder aus deinem echten Video | „passt“ sagen |
| 5 Storyboard | pro Satz festlegen, was im Bild passiert | schlägt je Szene 2 bis 4 Grafiken vor, mit einem roten Faden durchs ganze Video | je Szene wählen |
| 6 Schnitt + Feinschliff | Farbe, Zoom, Ton, Export, Kontrolle | 5 Licht-Varianten, Augen auf gleicher Höhe, Zoom-Sprung auf jedem Schnitt, Sounds, Hook-Versionen, Endkontrolle | Licht wählen, Sounds anhören, Vorschau ansehen |

Nur den Rohschnitt willst du? `/schnitt dein-video.mov nur rohschnitt` hört nach Schritt 2 auf und
funktioniert auch mit Querformat.

## Was du brauchst

| Was | Wofür | Kosten |
|---|---|---|
| Claude Pro oder Max | Schneiden braucht viele Token. Wer regelmäßig schneidet, braucht mehr Limit | dein Abo |
| Claude Code (Terminal oder Code-Tab der Desktop-App) | hier läuft der Skill | im Abo enthalten |
| [Deepgram-Konto](https://console.deepgram.com) | Transkript mit Zeitstempel für jedes Wort, darauf baut alles auf | Startguthaben bei der Anmeldung, danach nach Verbrauch |
| ffmpeg, Node 20 oder neuer, Python 3.10 oder neuer | schneiden, Grafiken, Messungen | kostenlos, Claude installiert sie beim ersten Lauf über Homebrew |

Den Deepgram-Schlüssel trägst du in `~/.config/schnitt/.env` ein, die Datei legt der erste Lauf an:

```
DEEPGRAM_API_KEY=<dein Schlüssel>
```

Nutzt du schon [`watch`](https://github.com/epictaste/claude-eyes), wird der Schlüssel aus
`~/.config/watch/.env` mitgelesen.

## Ehrlich: was hält und was nicht

**Was hält:** Takes auswählen, Versprecher und Räusperer finden, Schnitte in die Stille legen,
Zoom, Augenhöhe, Untertitel und die technische Endkontrolle. Das sind die Arbeiten, die beim
Schneiden am meisten Zeit fressen, und die nimmt dir Claude ab.

**Rendern braucht Zeit und Token.** Das liegt an der Rechenleistung beim Rendern, nicht an Claude.
Ein Video mit mehreren Versionen kann inklusive deiner Entscheidungen zwischendurch mehrere Stunden
brauchen. Deshalb hat jeder Schritt einen Prüfpunkt: erst Tabelle, dann Vorschau, dann
Standbilder, erst dann der teure Render.

**Sounds sind die schwächste Stelle.** Claude kann nicht hören. Die Effekte werden per ffmpeg
erzeugt, sitzen auf sichtbaren Ereignissen und liegen unter deiner Stimme. Ob sie passen,
entscheidest du mit deinen Ohren.

**Geschmack bleibt bei dir.** Claude baut, was du auswählst. Welche Grafik, welcher Look, welches
Licht: das fragt der Skill jedes Mal, statt es selbst zu entscheiden.

## Was du bekommst

```
schnitt-dein-video/
├── rohschnitt/   Transkript, Take-Auswahl, Schnittkanten
├── stil/         Bilder deiner Referenzen, Stilbeschreibung
├── schnitt/      Versionen, Wortzeiten, Augen, Licht, Sounds
├── remotion/     das Projekt mit Grafiken und Untertiteln, im Browser anschaubar (npm run studio)
└── aus/          fertige Videos je Version, Abnahme-Bericht, 720p-Vorschau fürs Handy
```

Der Skill postet nichts, lädt nichts hoch und schreibt niemandem. Am Ende stehen Dateipfade.

## Logos

Echte Logos statt Platzhalter-Kästchen: leg die Logos der Apps und Marken, über die du sprichst, in
`schnitt-<name>/remotion/public/logos/`. Auf dem Mac kann Claude das Icon einer installierten App
selbst aus dem Programmpaket holen. Nimm nur Logos, die du zeigen darfst.

## Aufbau

```
.
├── skills/schnitt/
│   ├── SKILL.md                 Ablauf der sechs Schritte
│   ├── referenz/                ein Dokument je Schritt, Regeln für Grafiken, Standard-Stil
│   ├── scripts/                 Python- und Shell-Werkzeuge (setup, transkript, schnitt, geruest, bauen, abnahme …)
│   ├── assets/                  Farb-LUTs, Augen-Werkzeug (Swift)
│   └── template/                Remotion-Projekt, wird je Video kopiert
├── hooks/                       Status-Hook beim Start von Claude Code
├── .claude-plugin/              plugin.json und marketplace.json
└── tests/                       pytest mit synthetischen Videos, ohne Netz
```

## Entwickeln

```bash
python3 -m pytest -q
cd skills/schnitt/template && npm ci && npx tsc --noEmit
```

Versionen stehen in [CHANGELOG.md](CHANGELOG.md), was deinen Rechner verlässt, steht in
[SECURITY.md](SECURITY.md).

## Lizenz

MIT, siehe [LICENSE](LICENSE). Gebaut mit [Remotion](https://remotion.dev), ffmpeg und
[Deepgram](https://deepgram.com). Remotion hat eine eigene Lizenz: für Einzelpersonen und kleine
Firmen kostenlos, größere Firmen brauchen eine Firmenlizenz, siehe
[remotion.dev/license](https://remotion.dev/license).
