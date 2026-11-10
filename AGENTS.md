# schnitt

Agent-Skill-Paket, mit dem ein Agent ein selbst gedrehtes Video (Person spricht in die Kamera) in
sechs Schritten schneidet: Rohschnitt, Stil aus Referenzen, Stilprobe, Storyboard, Feinschliff,
Endkontrolle. Die Python-Skripte steuern ffmpeg, ffprobe, Remotion und die Deepgram-API.

## Aufbau

- `skills/schnitt/SKILL.md`: der Ablauf. Maßgeblich für das Verhalten, unter 400 Zeilen halten.
- `skills/schnitt/referenz/`: `schritt-1-voraussetzungen.md` bis `schritt-6-feinschliff.md`,
  `regeln-grafiken.md` (Brief für Bau-Agents), `stil-standard.md` (Standard-Look und Schema von `stil.json`).
- `skills/schnitt/scripts/`: Werkzeuge je Schritt. `geruest.py` schreibt aus `schnitt/meta.json`,
  `schnitt/woerter.json` und `spec.json` das Gerüst `remotion/src/reel.ts` samt Szenen-Tabelle.
- `skills/schnitt/template/`: das Remotion-Projekt, das je Video nach `schnitt-<name>/remotion/`
  kopiert wird. `src/reel.ts` ist ein Beispiel und wird pro Projekt von `geruest.py` ersetzt.
- `hooks/`: Status-Hook beim Start von Claude Code.
- `.claude-plugin/`: Manifeste.
- `tests/`: pytest, Videos per ffmpeg erzeugt, kein Netz.

## Orientierung

- **Das Produkt ist der Skill.** Die Skripte sind Werkzeug, die Regeln in SKILL.md und `referenz/`
  sind der Wert: Schnitte in die Stille, nur ganze Sätze, Wortmarken statt geschätzter Zeiten,
  Prüfpunkt vor jedem teuren Schritt, der Nutzer wählt das Design.
- **Ein Ordner, eine Einheit.** `SKILL.md`, `scripts/`, `referenz/` und `template/` liegen
  nebeneinander in `skills/schnitt/`. Nicht auseinanderziehen.
- **`SKILL_DIR` ist der Ordner der gelesenen SKILL.md.** Keine harness-spezifischen Variablen einführen.
- **Datenverträge sind eingefroren.** Dateinamen im Projektordner und die Exporte von `reel.ts`
  (`FPS`, `VERSIONEN`, `HOOK`, `SATZ2`, `TAKE_SCHNITTE`, `BODY_SCHNITTE`, `BODY`, `GESAMT`,
  `HOOK_WOERTER`, `BODY_WOERTER`, `BUEHNE`, `VOLL`, `KOPF_Y`, `AUGEN_Y`, `GESICHT_X`, `ZOOM`,
  `HOOK_SZENEN`, `SZENEN`, `VOLLBILD`) lesen mehrere Skripte. Umbenennen bricht die Abnahme.
- **`reel.ts` heißt klein, die Komposition `Komposition.tsx`.** macOS unterscheidet Groß- und
  Kleinschreibung nicht, `Reel.tsx` neben `reel.ts` bricht den Import.
- **Kein Audio-Element im Remotion-Projekt**, auch nicht im Kommentar. `bauen.sh` sucht danach und
  rendert sonst den Ton selbst, statt die Mischung aus `--ton-video` zu nehmen.

## Befehle

```bash
python3 -m pytest -q
cd skills/schnitt/template && npm ci && npx tsc --noEmit
cd skills/schnitt/template && npx remotion still Zone-v1 /tmp/schnitt-probe.png --frame=150
```

## Regeln

- Version gleich halten in `skills/schnitt/SKILL.md` (Frontmatter), `.claude-plugin/plugin.json`
  und `.claude-plugin/marketplace.json`.
- Nie einen Schlüssel, eine `.env` oder ein gerendertes Video committen.
- Renders loggen in eine Datei, nie in eine Pipe, die früh schließt.
- Ein Projekt hat sein eigenes `public/`. Nie auf einen großen geteilten Ordner zeigen.
- Abweichende Bildanzahl ist ein Fehler, keine Warnung.
- Remotion bleibt auf 4.0.424 gepinnt, bis ein Update mit `npx tsc --noEmit` und einem Standbild geprüft ist.
- Deutsch mit echten Umlauten in allem, was Nutzer lesen.
