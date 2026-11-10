#!/usr/bin/env python3
"""Räusperer an Clip-Anfängen und -Enden suchen (Schritt 2, nach straffen.py und ausklang.py).

Deepgram schlägt einen Räusperer direkt vor dem Satz oft dem ersten Wort zu, er
landet dann mit im Take. Muster am Anfang: kurzer lauter Block (mindestens 2
Frames über -45 dB in den ersten 25 Frames), dann mindestens 6 Frames am Stück
unter -55 dB, dann wieder Sprache. Am Ende dasselbe Muster rückwärts gelesen.

Jeder Treffer ist ein Verdacht, kein Urteil: Clip-Start hinter die Stille legen
(1 Frame Luft), den Ausschnitt gegentranskribieren, erst dann weiter.

Aufruf: python raeusper_check.py <rohschnitt-ordner>
Braucht numpy (Python-Umgebung aus setup.py).
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


def muster(pegel: list[float]) -> tuple[bool, int, int]:
    """(Treffer, Blocklänge in Frames, Stille-Länge in Frames)."""
    for s in range(2, 26):
        e = s
        while e < len(pegel) and pegel[e] < -55:
            e += 1
        if e - s >= 6 and e < len(pegel) and sum(p > -45 for p in pegel[:s]) >= 2:
            return True, s, e - s
    return False, 0, 0


def pruefen(ordner: Path) -> list[dict]:
    k = json.loads((ordner / "kanten.json").read_text())
    x, sr = lade_audio(ordner / "audio.wav")

    def db(f: int) -> float:
        seg = x[int(f / FPS * sr):int((f + 1) / FPS * sr)]
        return float(20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-9)) if len(seg) else -120.0

    treffer = []
    for n, c in enumerate(k["clips"], 1):
        a, b = c["vonFrame"], c["bisFrame"]
        ok, block, stille = muster([db(f) for f in range(a, min(b, a + 45))])
        if ok:
            treffer.append({"clip": n, "wo": "anfang", "frame": a, "block": block, "stille": stille})
            print(f"Clip {n} Anfang {a}: Block {block} Frames, dann {stille} Frames Stille -> Verdacht Räusperer")
        ok, block, stille = muster([db(f) for f in range(b - 1, max(a, b - 45), -1)])
        if ok:
            treffer.append({"clip": n, "wo": "ende", "frame": b, "block": block, "stille": stille})
            print(f"Clip {n} Ende {b}: Block {block} Frames vor der Kante, davor {stille} Frames Stille -> Verdacht Räusperer")
    print(f"fertig, {len(treffer)} Verdachtsfälle in {ordner.name}")
    return treffer


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ordner", type=Path)
    pruefen(ap.parse_args().ordner.resolve())


if __name__ == "__main__":
    main()
