#!/usr/bin/env python3
"""Leise Ausklänge zurückholen und lange Wörter am Clip-Anfang melden (Schritt 2, nach straffen.py).

straffen.py schneidet mit -45 dB. Leise Wortenden (-46 bis -50 dB) fallen dabei
manchmal mit weg, hörbar als abgeschnittenes Wort. Dieses Skript verfolgt jedes
Clip-Ende frameweise weiter, bis zwei Frames unter -56 dB liegen. Liegt dazwischen
ein Frame über -50,5 dB, wird das Ende bis dorthin verlängert (plus 2 Frames),
nie über den Anfang des nächsten Clips hinaus.

Außerdem: Wörter über 0,6 s in den ersten 2 s eines Clips. Deepgram klebt
Räusperer und Fehlstarts gern an das erste Wort. Jeden Treffer im Pegel
ansehen (raeusper_check.py) und den Ausschnitt gegentranskribieren.

Aufruf: python ausklang.py <rohschnitt-ordner> [weitere ...]
Braucht numpy (Python-Umgebung aus setup.py). Schreibt kanten.json neu.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from straffen import lade_audio  # noqa: E402

import numpy as np  # noqa: E402

FPS = 30
STILL_DB = -56.0
LAUT_DB = -50.5
SUCHE_FRAMES = 20
LANGES_WORT = 0.6


def ausklang(ordner: Path) -> dict:
    x, sr = lade_audio(ordner / "audio.wav")

    def db(f: int) -> float:
        seg = x[int(f / FPS * sr):int((f + 1) / FPS * sr)]
        if len(seg) == 0:
            return -120.0
        return float(20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-9))

    k = json.loads((ordner / "kanten.json").read_text())
    woerter = json.loads((ordner / "woerter.json").read_text())
    clips = k["clips"]
    for i, c in enumerate(clips):
        b = c["bisFrame"]
        grenze = clips[i + 1]["vonFrame"] if i + 1 < len(clips) else 10 ** 9
        f, letzte_laut = b, None
        while f < b + SUCHE_FRAMES and f + 1 < grenze:
            if db(f) < STILL_DB and db(f + 1) < STILL_DB:
                break
            if db(f) > LAUT_DB:
                letzte_laut = f
            f += 1
        if letzte_laut is not None and letzte_laut >= b:
            neu = min(letzte_laut + 2, grenze)
            print(f"Clip {i + 1}: Ende {b} -> {neu}")
            c["bisFrame"] = neu
            c["bis"] = round(neu / FPS, 3)
        for w in woerter:
            if c["von"] - 0.05 <= w["start"] < c["von"] + 2 and w["end"] - w["start"] > LANGES_WORT:
                print(f"Clip {i + 1}: langes Wort am Anfang „{w['wort']}“ {w['end'] - w['start']:.2f} s ab {w['start']:.2f} s, prüfen")
    k["frames"] = sum(c["bisFrame"] - c["vonFrame"] for c in clips)
    (ordner / "kanten.json").write_text(json.dumps(k, ensure_ascii=False, indent=1))
    print(f"{ordner.name}: {k['frames'] / FPS:.2f} s")
    return k


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ordner", type=Path, nargs="+")
    args = ap.parse_args()
    for o in args.ordner:
        ausklang(o.resolve())


if __name__ == "__main__":
    main()
