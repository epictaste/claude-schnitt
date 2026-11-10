#!/usr/bin/env python3
"""Ton je Version direkt aus der Originaldatei schneiden (Schritt 5).

Nie audio.wav nehmen: das ist die 16-kHz-Fassung für Deepgram, ihr fehlt alles
über 8 kHz. Hier kommt der Ton in voller Qualität (48 kHz) aus dem Original,
auf genau die Clips aus kanten.json, die bereiche.json der Version nennt.

Aufruf: python ton_neu.py <rohschnitt-ordner> <schnitt-ordner>
Ergebnis: <schnitt>/<version>-neu.mp4 (nur Ton, AAC 192k, 48 kHz).
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

FPS = 30


def teile_der_version(clips: list[dict], bereiche: list[list[int]]) -> list[tuple[int, int]]:
    cum = [0]
    for c in clips:
        cum.append(cum[-1] + c["bisFrame"] - c["vonFrame"])
    teile = []
    for a, e in bereiche:
        for i, c in enumerate(clips):
            if cum[i] >= a and cum[i + 1] <= e:
                teile.append((c["vonFrame"], c["bisFrame"]))
    return teile


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rohschnitt", type=Path)
    ap.add_argument("ziel", type=Path)
    args = ap.parse_args()
    k = json.loads((args.rohschnitt / "kanten.json").read_text())
    b = json.loads((args.ziel / "bereiche.json").read_text())
    for v, d in b.items():
        teile = teile_der_version(k["clips"], d["bereiche"])
        fc = "".join(f"[0:a]atrim=start={x / FPS:.6f}:end={y / FPS:.6f},asetpts=PTS-STARTPTS[a{i}];" for i, (x, y) in enumerate(teile))
        fc += "".join(f"[a{i}]" for i in range(len(teile))) + f"concat=n={len(teile)}:v=0:a=1[a]"
        aus = args.ziel / f"{v}-neu.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", k["quelle"], "-filter_complex", fc, "-map", "[a]",
                        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(aus)], check=True)
        dauer = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(aus)],
                                     capture_output=True, text=True).stdout)
        print(v, f"{dauer:.3f} s, Soll {sum(y - x for x, y in teile) / FPS:.3f} s")


if __name__ == "__main__":
    main()
