#!/usr/bin/env python3
"""Stil-Referenzen ansehen (Schritt 3): je Referenzvideo 6 Frames und ein Kontaktbogen.

Der Nutzer gibt 2 bis 3 Videos, deren Look er mag (eigene Dateien, kein Download).
Das Skript zieht je Video 6 gleichmäßig verteilte Frames (die ersten und letzten
5 % ausgelassen) und legt sie als Kontaktbogen nebeneinander. Claude sieht sich
die Bögen an und schreibt daraus stil.json und stil.md.

Aufruf: python stil_bilder.py <video> [video ...] --aus <ordner> [--frames 6]
Ausgabe je Video: <name>-1.jpg bis <name>-6.jpg und <name>-bogen.jpg.
Braucht pillow (Python-Umgebung aus setup.py).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
from bild_helfer import schrift  # noqa: E402

KACHEL_HOEHE = 640


def zeitpunkte(dauer: float, anzahl: int) -> list[float]:
    """`anzahl` Zeitpunkte gleichmäßig zwischen 5 % und 95 % der Dauer."""
    a, e = dauer * 0.05, dauer * 0.95
    if anzahl == 1:
        return [round((a + e) / 2, 3)]
    return [round(a + (e - a) * i / (anzahl - 1), 3) for i in range(anzahl)]


def bilder(video: Path, aus: Path, anzahl: int) -> Path:
    aus.mkdir(parents=True, exist_ok=True)
    dauer = config.duration_seconds(video)
    font = schrift(28)
    kacheln = []
    for i, t in enumerate(zeitpunkte(dauer, anzahl), 1):
        ziel = aus / f"{video.stem}-{i}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
                        "-q:v", "3", str(ziel)], check=True)
        im = Image.open(ziel).convert("RGB")
        k = im.resize((max(1, round(im.width * KACHEL_HOEHE / im.height)), KACHEL_HOEHE))
        d = ImageDraw.Draw(k)
        d.rectangle((0, 0, 150, 40), fill=(0, 0, 0))
        d.text((8, 4), f"{t:.1f} s", font=font, fill="white")
        kacheln.append(k)
    breite = sum(k.width for k in kacheln) + 10 * (len(kacheln) - 1)
    bogen = Image.new("RGB", (breite, KACHEL_HOEHE), "black")
    x = 0
    for k in kacheln:
        bogen.paste(k, (x, 0))
        x += k.width + 10
    pfad = aus / f"{video.stem}-bogen.jpg"
    bogen.save(pfad, quality=86)
    print(pfad)
    return pfad


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("videos", type=Path, nargs="+")
    ap.add_argument("--aus", type=Path, required=True)
    ap.add_argument("--frames", type=int, default=6)
    args = ap.parse_args()
    for v in args.videos:
        if not v.exists():
            sys.exit(f"Video nicht gefunden: {v}")
        bilder(v.resolve(), args.aus.resolve(), args.frames)


if __name__ == "__main__":
    main()
