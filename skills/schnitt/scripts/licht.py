#!/usr/bin/env python3
"""Licht-Varianten für den Take (Schritt 6): 5 Grades nebeneinander, mit Gesichtshelligkeit.

Aus einem Standbild des Takes (oder einem Frame eines Videos) entstehen fünf
Varianten von kräftig bis sehr hell, jede mit gemessener Helligkeit im Gesicht
(Mittelwert Luma 0 bis 255). Der Nutzer wählt eine, das Skript schreibt deren
ffmpeg-Kette als grade.txt, hd_take.py legt sie auf alle Versionen.

Aufruf:
  licht.py <bild.png|video.mp4> <ausgabe-ordner> [--zeit 5.0] [--gesicht x,y,b,h]
  licht.py --waehle 3 --grade-datei <schnitt-ordner>/grade.txt

Ausgabe: licht-1.png bis licht-5.png und licht-bogen.jpg (Kontaktbogen) im Ausgabe-Ordner.
--gesicht in 1080x1920-Koordinaten (Standard 450,920,140,200: Mitte, obere Bildhälfte des Kopfs).
Braucht pillow (Python-Umgebung aus setup.py).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageStat

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bild_helfer import schrift  # noqa: E402

#: Hauttöne neutral halten: Rot leicht raus, Rottöne entsättigt.
FARBE = "colorbalance=rm=-0.02:bm=0.01,huesaturation=hue=4:saturation=-0.25:colors=r:strength=1"
#: (Name, brightness, contrast, gamma)
VARIANTEN = [("1 kräftig", -0.195, 1.17, 0.97), ("2 etwas heller", -0.16, 1.17, 0.97), ("3 heller", -0.12, 1.15, 1.0),
             ("4 Mitten hoch", -0.16, 1.15, 1.10), ("5 sehr hell", -0.08, 1.12, 1.04)]


def kette(nr: int) -> str:
    _, b, c, g = VARIANTEN[nr - 1]
    return f"eq=brightness={b}:contrast={c}:gamma={g}:saturation=1.05,{FARBE}"


def standbild(quelle: Path, zeit: float, ziel: Path) -> Path:
    """Bild auf 1080x1920 bringen (Video: Frame bei `zeit` Sekunden)."""
    cmd = ["ffmpeg", "-v", "error", "-y"]
    if quelle.suffix.lower() not in (".png", ".jpg", ".jpeg"):
        cmd += ["-ss", f"{zeit:.3f}"]
    cmd += ["-i", str(quelle), "-frames:v", "1", "-vf",
            "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920", str(ziel)]
    subprocess.run(cmd, check=True)
    return ziel


def varianten(quelle: Path, aus: Path, zeit: float, gesicht: tuple[int, int, int, int]) -> list[tuple[str, float]]:
    aus.mkdir(parents=True, exist_ok=True)
    x, y, b, h = gesicht
    font = schrift(34)
    kacheln, werte = [], []
    with tempfile.TemporaryDirectory() as t:
        roh = standbild(quelle, zeit, Path(t) / "roh.png")
        for i, (name, *_rest) in enumerate(VARIANTEN, 1):
            ziel = aus / f"licht-{i}.png"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(roh), "-vf", kette(i), str(ziel)], check=True)
            im = Image.open(ziel).convert("RGB")
            yavg = ImageStat.Stat(im.crop((x, y, x + b, y + h)).convert("L")).mean[0]
            k = im.crop((0, 500, 1080, 1700)).resize((450, 500))
            d = ImageDraw.Draw(k)
            d.rectangle((0, 0, 450, 92), fill=(0, 0, 0))
            d.text((12, 6), name, font=font, fill="white")
            d.text((12, 48), f"Gesicht {yavg:.0f}", font=font, fill=(255, 214, 10))
            kacheln.append(k)
            werte.append((name, yavg))
            print(f"{name}: Gesicht {yavg:.0f}")
    bogen = Image.new("RGB", (450 * len(kacheln) + 10 * (len(kacheln) - 1), 500), "black")
    for i, k in enumerate(kacheln):
        bogen.paste(k, (i * 460, 0))
    bogen.save(aus / "licht-bogen.jpg", quality=88)
    print(aus / "licht-bogen.jpg")
    return werte


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("quelle", type=Path, nargs="?")
    ap.add_argument("ausgabe", type=Path, nargs="?")
    ap.add_argument("--zeit", type=float, default=5.0, help="Sekunde im Video für das Standbild")
    ap.add_argument("--gesicht", default="450,920,140,200")
    ap.add_argument("--waehle", type=int, choices=range(1, len(VARIANTEN) + 1), help="Variante als grade.txt schreiben")
    ap.add_argument("--grade-datei", type=Path)
    args = ap.parse_args()
    if args.waehle:
        if not args.grade_datei:
            sys.exit("--waehle braucht --grade-datei <schnitt-ordner>/grade.txt")
        args.grade_datei.parent.mkdir(parents=True, exist_ok=True)
        args.grade_datei.write_text(kette(args.waehle) + "\n")
        print(f"{args.grade_datei}: Variante {VARIANTEN[args.waehle - 1][0]}")
        return
    if not args.quelle or not args.ausgabe:
        ap.error("Quelle und Ausgabe-Ordner angeben")
    gesicht = tuple(int(v) for v in args.gesicht.split(","))
    varianten(args.quelle.resolve(), args.ausgabe.resolve(), args.zeit, gesicht)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
