#!/usr/bin/env python3
"""Sucht digitale Stille (echte Null-Samples) in der Tonspur eines Videos (Schritt 6).

Hintergrund: Wird ein Video in Teilen gerendert und mit `ffmpeg concat -c copy`
zusammengesetzt, fällt an der Naht ein AAC-Paket weg. Das Bild bleibt sauber, im Ton
klafft ein Loch von rund 15 ms. Im laufenden Vokal hört man das deutlich.

Aufruf: python naht_check.py <datei.mp4> [weitere.mp4 ...]
        python naht_check.py --selbsttest
Rückgabe 1, wenn irgendwo ein Loch nach Sekunde 0,1 liegt. Braucht numpy.
"""
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

FENSTER_S = 0.005


def dauer(datei):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", datei], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def loecher(datei):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        pfad = tmp.name
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", datei, "-ac", "1",
                        "-ar", "48000", "-c:a", "pcm_s16le", pfad], check=True)
        with wave.open(pfad) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    finally:
        os.unlink(pfad)

    n = int(sr * FENSTER_S)
    stumm = [i / sr for i in range(0, len(x) - n, n) if np.abs(x[i:i + n]).max() == 0]
    gruppen = []
    for t in stumm:
        if gruppen and t - gruppen[-1][1] < 0.02:
            gruppen[-1][1] = t
        else:
            gruppen.append([t, t])
    return [(a, b + FENSTER_S) for a, b in gruppen]


def main(dateien):
    schlecht = False
    for datei in dateien:
        # AAC-Encoder legen an Dateianfang und -ende Stille, das ist normal. Nur die Mitte zählt.
        ende = dauer(datei)
        treffer = [(a, b) for a, b in loecher(datei) if 0.1 < a < ende - 0.1]
        if treffer:
            schlecht = True
            print(f"FEHLER {datei}")
            for a, b in treffer:
                print(f"   Loch bei {a:.3f} s (Frame {a * 30:.0f}), {(b - a) * 1000:.0f} ms")
        else:
            print(f"ok     {datei}")
    return 1 if schlecht else 0


def demo():
    """Selbsttest: ein erzeugtes Loch muss gefunden werden, sauberer Ton nicht."""
    with tempfile.TemporaryDirectory() as d:
        heil, kaputt = f"{d}/heil.mp4", f"{d}/kaputt.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=440:d=3",
                        "-c:a", "aac", heil], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=440:d=3",
                        "-af", "volume=enable='between(t,1.5,1.52)':volume=0",
                        "-c:a", "aac", kaputt], check=True)
        mitte = lambda f: [t for t in loecher(f) if 0.1 < t[0] < dauer(f) - 0.1]
        assert not mitte(heil), "sauberer Ton fälschlich bemängelt"
        assert mitte(kaputt), "erzeugtes Loch nicht gefunden"
        print("Selbsttest ok")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if len(sys.argv) > 1 else 2)
    if sys.argv[1] == "--selbsttest":
        demo()
    else:
        sys.exit(main(sys.argv[1:]))
