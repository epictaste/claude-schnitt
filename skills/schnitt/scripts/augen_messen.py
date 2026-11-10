#!/usr/bin/env python3
"""Augenhöhe und Gesichtsmitte je Take-Clip messen (Schritt 6).

Damit Augen und Gesicht nach jedem Schnitt auf derselben Höhe bleiben, misst das
Skript je Clip drei Frames (Anfang, Mitte, Ende) mit macOS Vision (Programm
`augen`, kompiliert von setup.py) und nimmt den Median.

Aufruf: python augen_messen.py <schnitt-ordner> [--werkzeug <pfad-zu-augen>]
Liest meta.json und <v>-hd.mp4, schreibt augen.json
{version: [[startFrame, augenY, augenX], ...]} in 1080x1920-Koordinaten.
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

FPS = config.FPS


def werte_lesen(zeilen: list[str], k: float) -> list[tuple[float, float]]:
    """Ausgabezeilen von `augen` (datei y x) in 1080er Koordinaten, Fehlzeilen fallen weg."""
    werte = []
    for z in zeilen:
        teile = z.split()
        if len(teile) < 3 or "KEIN_GESICHT" in z or "FEHLER" in z:
            continue
        werte.append((float(teile[-2]) * k, float(teile[-1]) * k))
    return werte


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ziel", type=Path)
    ap.add_argument("--werkzeug", type=Path, default=config.augen_werkzeug())
    args = ap.parse_args()
    if not args.werkzeug.exists():
        sys.exit(f"{args.werkzeug} fehlt. Erst setup.py ausführen (braucht macOS und swiftc).")
    ziel = args.ziel
    meta = json.loads((ziel / "meta.json").read_text())
    aus: dict = {}
    for v, hook in meta["HOOK"].items():
        video = ziel / f"{v}-hd.mp4"
        breite = config.video_stream(video)["width"]
        k = 1080 / breite
        gesamt = hook + meta["BODY"]
        grenzen = [0] + meta["TAKE_SCHNITTE"][v] + [gesamt]
        liste = []
        with tempfile.TemporaryDirectory() as t:
            for a, b in zip(grenzen, grenzen[1:]):
                if b - a < 1:
                    continue
                bilder = []
                for f in sorted({min(a + 3, b - 1), (a + b) // 2, max(a, b - 4)}):
                    p = f"{t}/f{f}.png"
                    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{f / FPS:.4f}", "-i", str(video), "-frames:v", "1", p],
                                   check=True)
                    bilder.append(p)
                zeilen = subprocess.run([str(args.werkzeug), *bilder], capture_output=True, text=True).stdout.splitlines()
                werte = werte_lesen(zeilen, k)
                if werte:
                    liste.append([a, round(statistics.median(w[0] for w in werte)), round(statistics.median(w[1] for w in werte))])
        aus[v] = liste
        print(v, " ".join(f"{a}:{y}/{x}" for a, y, x in liste) or "kein Gesicht gefunden")
    (ziel / "augen.json").write_text(json.dumps(aus))


if __name__ == "__main__":
    main()
