#!/usr/bin/env python3
"""Take-Ränder straffen (Schritt 2, nach `schnitt.py kanten`).

Zieht jede Clip-Kante in kanten.json frameweise an die Sprache heran, bis nur
noch ein stiller Frame vor dem ersten und nach dem letzten Laut bleibt.
Still heißt: Pegel unter --schwelle dB (Standard -45). Strenger (z. B. -38)
kappt leise Wortenden wie „s“ oder „f“. Pausen innerhalb eines Takes bleiben.
Danach immer ausklang.py laufen lassen, er holt leise Ausklänge zurück.

Aufruf: python straffen.py <rohschnitt-ordner> [weitere ...] [--schwelle -45]
Braucht numpy (Python-Umgebung aus setup.py).
"""
from __future__ import annotations

import argparse
import json
import wave
from pathlib import Path

import numpy as np

FPS = 30


def lade_audio(pfad: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(pfad)) as w:
        sr, ch = w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    if ch > 1:
        x = x.reshape(-1, ch).mean(1)
    return x, sr


def straffen(ordner: Path, schwelle: float = -45.0) -> dict:
    x, sr = lade_audio(ordner / "audio.wav")

    def still(f: int) -> bool:  # Frame f = [f/30, (f+1)/30)
        seg = x[int(f / FPS * sr):int((f + 1) / FPS * sr)]
        if len(seg) == 0:
            return True
        return 20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-9) < schwelle

    k = json.loads((ordner / "kanten.json").read_text())
    vorher = k["frames"]
    for c in k["clips"]:
        v, b = c["vonFrame"], c["bisFrame"]
        while v + 2 < b and still(v) and still(v + 1):
            v += 1  # ein stiller Frame bleibt vor der Sprache
        while b - 2 > v and still(b - 1) and still(b - 2):
            b -= 1  # ein stiller Frame bleibt nach der Sprache
        c["vonFrame"], c["bisFrame"] = v, b
        c["von"], c["bis"] = round(v / FPS, 3), round(b / FPS, 3)
    k["frames"] = sum(c["bisFrame"] - c["vonFrame"] for c in k["clips"])
    (ordner / "kanten.json").write_text(json.dumps(k, ensure_ascii=False, indent=1))
    kurz = [(c.get("clip"), c["bisFrame"] - c["vonFrame"]) for c in k["clips"] if c["bisFrame"] - c["vonFrame"] < 8]
    print(f"{ordner.name}: {vorher / FPS:.2f} s -> {k['frames'] / FPS:.2f} s", "kurze Stücke:", kurz or "keine")
    return k


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ordner", type=Path, nargs="+")
    ap.add_argument("--schwelle", type=float, default=-45.0)
    args = ap.parse_args()
    for o in args.ordner:
        straffen(o.resolve(), args.schwelle)


if __name__ == "__main__":
    main()
