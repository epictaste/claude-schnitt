# Sicherheit

`/schnitt` lässt ffmpeg, ffprobe, Python-Skripte und Remotion auf deinem Rechner laufen. Hier steht
genau, was ihn verlässt und was nicht.

## Was rausgeht

- **Die Tonspur, an Deepgram.** Für die Wortzeiten zieht der Skill eine Mono-Tonspur aus dem Video
  und schickt sie an `api.deepgram.com/v1/listen`. Das ist die einzige Verbindung, die Inhalte von
  dir trägt. Das gilt auch für Referenzvideos, wenn du für sie ein Transkript willst.
- **npm und ein Headless-Browser beim ersten Projekt.** Remotion lädt seine Pakete und einen
  Chromium beim ersten Rendern.
- **Schriften von Google Fonts beim Rendern.** Remotion holt die Schriften aus `stil.json`.
- **Homebrew beim Einrichten**, wenn ffmpeg oder Node fehlen und du der Installation zustimmst.

## Was lokal bleibt

- **Das Video selbst.** Es wird nie hochgeladen. Schneiden, Messen, Rendern und die Endkontrolle
  laufen mit lokalen Programmen.
- **Die fertigen Dateien.** Sie liegen im Projektordner `schnitt-<name>/` und sonst nirgends.
- **Dein Schlüssel.** Er steht in `~/.config/schnitt/.env` (Rechte 0600) oder in
  `~/.config/watch/.env`, wenn du den `watch`-Skill nutzt. Er wird nie ausgegeben, geloggt oder in
  eine Ausgabedatei geschrieben.

## Faustregeln

- **`.env` nie committen.** Sie steht in `.gitignore`.
- **Verpixeln, was niemand lesen soll.** Der Baustein `Mosaik` ist für ganze Prompts, Schlüssel und
  private Pfade in Bildschirmaufnahmen da.
- **Der Skill verschickt nichts.** Er postet nicht, lädt nichts hoch, schreibt niemandem. Am Ende
  stehen Dateipfade.

## Sicherheitslücke melden

Bitte privat melden, über
[GitHub Security Advisories](https://github.com/epictaste/claude-schnitt/security/advisories/new). Ein öffentliches Issue würde die Lücke für alle sichtbar machen, bevor sie geschlossen ist.
