#!/usr/bin/env python3
"""Drei Stilproben aus dem echten Video (Schritt 4): Hook mit Plakat, Body weit, Body nah, alle mit Untertitel.

Zieht zwei Frames aus dem Take (Hook und Body) nach <remotion>/public/stilprobe/,
rendert daraus mit der Komposition `Stilprobe` der Vorlage drei Standbilder
(`npx remotion still`) und legt sie als Kontaktbogen nebeneinander. Der Nutzer
schaut den Bogen an und sagt „passt“ oder was anders soll.

Aufruf:
  plakate.py <remotion-ordner> <take.mp4> --aus <ordner> --plakat "Zeile 1" "Zeile 2" \\
             [--untertitel "ein Satz aus dem Video"] [--hook-zeit 1.0] [--body-zeit 8.0] \\
             [--zoom 1.1] [--augen-y 1000] [--gesicht-x 540] [--entry src/index.ts]

Ausgabe: stilprobe-plakat.png, stilprobe-weit.png, stilprobe-nah.png und stilprobe-bogen.jpg in --aus.
Braucht pillow (Python-Umgebung aus setup.py) und die installierte Vorlage (npm ci).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bild_helfer import schrift  # noqa: E402

KOMPOSITION = "Stilprobe"
MODI = ("plakat", "weit", "nah")


def frame_ziehen(video: Path, zeit: float, ziel: Path) -> None:
    ziel.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{zeit:.3f}", "-i", str(video), "-frames:v", "1", "-vf",
                    "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920", str(ziel)], check=True)


def props_fuer(modus: str, args) -> dict:
    return {
        "bild": f"stilprobe/{'hook' if modus == 'plakat' else 'body'}.png",
        "modus": modus,
        "plakat": args.plakat if modus == "plakat" else [],
        # Untertitel in allen drei Bildern: Lage unter dem Kinn hängt am Zoom, also je Bild prüfen.
        "untertitel": args.untertitel,
        "zoom": args.zoom,
        "augenY": args.augen_y,
        "gesichtX": args.gesicht_x,
    }


def bogen(bilder: list[Path], ziel: Path) -> Path:
    font = schrift(30)
    kacheln = []
    for p in bilder:
        k = Image.open(p).convert("RGB").resize((360, 640))
        d = ImageDraw.Draw(k)
        d.rectangle((0, 0, 360, 44), fill=(0, 0, 0))
        d.text((10, 6), p.stem.replace("stilprobe-", ""), font=font, fill="white")
        kacheln.append(k)
    b = Image.new("RGB", (360 * len(kacheln) + 10 * (len(kacheln) - 1), 640), "black")
    for i, k in enumerate(kacheln):
        b.paste(k, (i * 370, 0))
    b.save(ziel, quality=88)
    return ziel


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("remotion", type=Path, help="Remotion-Projekt (Kopie der Vorlage)")
    ap.add_argument("take", type=Path, help="Take-Video, z. B. rohschnitt/<name>/schnitt-hd.mp4")
    ap.add_argument("--aus", type=Path, required=True)
    ap.add_argument("--plakat", nargs="+", default=[], help="Zeilen des Hook-Plakats")
    ap.add_argument("--untertitel", default="")
    ap.add_argument("--hook-zeit", type=float, default=1.0)
    ap.add_argument("--body-zeit", type=float, default=8.0)
    ap.add_argument("--zoom", type=float, default=1.1)
    ap.add_argument("--augen-y", type=int, default=1000)
    ap.add_argument("--gesicht-x", type=int, default=540)
    ap.add_argument("--entry", default="src/index.ts")
    args = ap.parse_args()

    remotion, aus = args.remotion.resolve(), args.aus.resolve()
    aus.mkdir(parents=True, exist_ok=True)
    take = args.take.resolve()
    frame_ziehen(take, args.hook_zeit, remotion / "public" / "stilprobe" / "hook.png")
    frame_ziehen(take, args.body_zeit, remotion / "public" / "stilprobe" / "body.png")
    fertig = []
    with tempfile.TemporaryDirectory() as t:
        for modus in MODI:
            pf = Path(t) / f"{modus}.json"
            pf.write_text(json.dumps(props_fuer(modus, args), ensure_ascii=False))
            ziel = aus / f"stilprobe-{modus}.png"
            r = subprocess.run(["npx", "remotion", "still", args.entry, KOMPOSITION, str(ziel), f"--props={pf}"],
                               cwd=remotion, capture_output=True, text=True)
            if r.returncode != 0:
                sys.exit(f"Stilprobe {modus} fehlgeschlagen:\n{(r.stderr or r.stdout)[-1500:]}")
            print(ziel, flush=True)
            fertig.append(ziel)
    print(bogen(fertig, aus / "stilprobe-bogen.jpg"))


if __name__ == "__main__":
    main()
