#!/usr/bin/env python3
"""Alle ausgewählten Takes als 720p-Vorschau mit Original-Ton (Schritt 2, Abschluss).

Vor dem Edit einmal komplett anhören: Versprecher, Räusperer und abgeschnittene
Wörter fallen hier auf, später kosten sie einen neuen Bau.

Bild aus <rohschnitt>/schnitt-hd.mp4 (hd_take.py), Ton je Clip aus der
Originaldatei (volle Abtastrate, nie audio.wav), Reihenfolge wie kanten.json.

Aufruf: python takes_vorschau.py <rohschnitt-ordner> [ausgabe.mp4]
Standard-Ausgabe: <projekt>/aus/takes-vorschau.mp4 (Projekt = zwei Ebenen über dem Rohschnitt-Ordner).
Die Datei danach öffnen (macOS: open <datei>).
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

FPS = 30


def vorschau(ordner: Path, aus: Path) -> Path:
    k = json.loads((ordner / "kanten.json").read_text())
    clips = k["clips"]
    fc = "".join(f"[1:a]atrim=start={c['vonFrame'] / FPS:.6f}:end={c['bisFrame'] / FPS:.6f},asetpts=PTS-STARTPTS[a{i}];"
                 for i, c in enumerate(clips))
    fc += "".join(f"[a{i}]" for i in range(len(clips))) + f"concat=n={len(clips)}:v=0:a=1[a];[0:v]scale=720:-2[v]"
    aus.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(ordner / "schnitt-hd.mp4"), "-i", k["quelle"],
                    "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "fast", "-crf", "25",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(aus)], check=True)
    print(aus)
    return aus


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ordner", type=Path)
    ap.add_argument("ausgabe", type=Path, nargs="?")
    args = ap.parse_args()
    ordner = args.ordner.resolve()
    vorschau(ordner, (args.ausgabe or ordner.parent.parent / "aus" / "takes-vorschau.mp4").resolve())


if __name__ == "__main__":
    main()
