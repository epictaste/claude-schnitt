#!/usr/bin/env python3
"""Scharfe Takes direkt aus dem Original bauen (Schritt 2 und Schritt 6).

Schritt 2: Die Clips aus kanten.json werden einzeln aus dem Original geschnitten
(nur diese Stücke, nicht das ganze 4K-Video) und als <rohschnitt>/schnitt-hd.mp4
geklebt. Größe 1350x2400 statt 1080x1920, damit der Zoom in Remotion (1,1 bis 1,4)
nichts hochskaliert. iPhone-HDR (HLG) wird per assets/hlg709.cube nach bt709
umgerechnet, variable Bildrate auf konstante 30 fps.

Schritt 6: Mit Versionen (v1=0:69,163: ...) schneidet es je Version Hook-Bereich +
Body aus schnitt-hd.mp4, legt Grade (grade.txt aus licht.py) und Farb-LUT drauf
und übernimmt den Ton aus <ton-von>/<version>-neu.mp4 (ton_neu.py).

Aufruf:
  hd_take.py <rohschnitt-ordner>                                  # nur schnitt-hd.mp4
  hd_take.py <rohschnitt-ordner> --ziel <schnitt-ordner>          # alle Versionen aus bereiche.json
  hd_take.py <rohschnitt-ordner> --ziel <schnitt-ordner> v1=0:93,544: v2=93:298,544: \\
             [--grade <schnitt>/grade.txt] [--lut look.cube] [--ton-von <ordner>]

Bereiche sind Rohschnitt-Frames (von:bis, bis leer = Ende). Ohne Angabe kommen sie aus
<ziel>/bereiche.json, das Licht ohne --grade aus <ziel>/grade.txt, falls vorhanden.
Ergebnis: <ziel>/<version>-hd.mp4 (H.264 crf 14, 30 fps, Ton kopiert).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

FPS = config.FPS
BT709 = "setparams=range=tv:color_primaries=bt709:color_trc=bt709:colorspace=bt709"
FARBTAGS = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]


def zaehlen(p: Path) -> int:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-count_packets", "-show_entries",
                          "stream=nb_read_packets", "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout
    return config.first_int(out) or 0


def segment_filter(quelle: Path, breite: int, hoehe: int) -> str:
    """Skalieren (füllend, mittig beschnitten), HDR nach bt709, 30 fps."""
    groesse = f"scale={breite}:{hoehe}:force_original_aspect_ratio=increase:flags=lanczos"
    if config.ist_hlg(quelle):
        groesse = (f"scale={breite}:{hoehe}:force_original_aspect_ratio=increase:in_color_matrix=bt2020:in_range=tv:"
                   f"flags=lanczos,format=gbrp16le,lut3d={config.ASSETS / 'hlg709.cube'}")
    return f"{groesse},crop={breite}:{hoehe},format=yuv420p,fps={FPS},{BT709}"


def hd_rohschnitt(ordner: Path, breite: int, hoehe: int) -> Path:
    k = json.loads((ordner / "kanten.json").read_text())
    quelle = Path(k["quelle"])
    vf = segment_filter(quelle, breite, hoehe)
    segdir = ordner / "seg-hd"
    segdir.mkdir(exist_ok=True)
    stuecke = []
    for c in k["clips"]:
        von, bis = c["vonFrame"], c["bisFrame"]
        n = bis - von
        p = segdir / f"s{von}-{bis}-{breite}x{hoehe}.mp4"
        if not (p.exists() and zaehlen(p) == n):
            # -ss vor -i ist schnell, -frames:v statt -t trifft die Bildzahl exakt
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-threads", "4", "-ss", f"{von / FPS:.6f}", "-i", str(quelle),
                            "-map", "0:v:0", "-frames:v", str(n), "-vf", vf, "-filter_threads", "2",
                            "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-pix_fmt", "yuv420p", *FARBTAGS, str(p)],
                           check=True)
        ist = zaehlen(p)
        print(f"{p.name}: {ist} von {n} Frames", flush=True)
        if ist != n:
            sys.exit(f"Segment {p.name} hat {ist} statt {n} Frames")
        stuecke.append(p)
    liste = ordner / "liste-hd.txt"
    liste.write_text("".join(f"file '{p}'\n" for p in stuecke))
    roh = ordner / "schnitt-hd.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(liste), "-c:v", "copy", str(roh)],
                   check=True)
    soll = sum(c["bisFrame"] - c["vonFrame"] for c in k["clips"])
    gesamt = zaehlen(roh)
    print(f"HD-Rohschnitt {roh}: {gesamt} Frames (Soll {soll})", flush=True)
    if gesamt != soll:
        sys.exit("Bildzahl des HD-Rohschnitts weicht ab")
    return roh


def versionen_bauen(roh: Path, ziel: Path, versionen: list[str], grade: str, lut: Path, ton_von: Path) -> None:
    gesamt = zaehlen(roh)
    ziel.mkdir(parents=True, exist_ok=True)
    for arg in versionen:
        name, bereiche = arg.split("=", 1)
        teile = []
        for b in bereiche.split(","):
            a, e = b.split(":")
            teile.append((int(a), int(e) if e else gesamt))
        fc = "".join(f"[0:v]trim=start_frame={a}:end_frame={e},setpts=PTS-STARTPTS[v{i}];" for i, (a, e) in enumerate(teile))
        kette = f",{grade}" if grade else ""
        fc += ("".join(f"[v{i}]" for i in range(len(teile))) + f"concat=n={len(teile)}:v=1:a=0{kette},lut3d={lut},"
               f"format=yuv420p,{BT709}[v]")
        ton = ton_von / f"{name}-neu.mp4"
        if not ton.exists():
            sys.exit(f"Ton fehlt: {ton} (erst ton_neu.py)")
        aus = ziel / f"{name}-hd.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-threads", "4", "-i", str(roh), "-i", str(ton), "-filter_complex", fc,
                        "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-pix_fmt", "yuv420p",
                        "-r", str(FPS), "-g", str(FPS), *FARBTAGS, "-c:a", "copy", str(aus)], check=True)
        soll = sum(e - a for a, e in teile)
        print(f"{aus}: {zaehlen(aus)} Frames (Soll {soll})", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ordner", type=Path, help="Rohschnitt-Ordner mit kanten.json")
    ap.add_argument("versionen", nargs="*", help="v1=von:bis,von:bis ... (Rohschnitt-Frames)")
    ap.add_argument("--ziel", type=Path, help="Schnitt-Ordner für <version>-hd.mp4")
    ap.add_argument("--grade", type=Path, help="Datei mit ffmpeg-Filterkette (grade.txt)")
    ap.add_argument("--lut", type=Path, default=config.ASSETS / "identitaet.cube", help="Farb-LUT (Standard: neutral)")
    ap.add_argument("--ton-von", type=Path, help="Ordner mit <version>-neu.mp4 (Standard: --ziel)")
    ap.add_argument("--groesse", default="1350x2400", help="Breite x Höhe der Takes")
    args = ap.parse_args()

    ordner = args.ordner.resolve()
    breite, hoehe = (int(x) for x in args.groesse.lower().split("x"))
    # Fertige Segmente liegen im Cache, das Kleben dauert Sekunden. So passt schnitt-hd.mp4 immer zu kanten.json.
    roh = hd_rohschnitt(ordner, breite, hoehe)
    versionen = list(args.versionen)
    if args.ziel and not versionen:
        # Ohne Bereiche auf der Kommandozeile: alle Versionen aus <ziel>/bereiche.json (versionen.py).
        b = args.ziel / "bereiche.json"
        if not b.exists():
            sys.exit(f"{b} fehlt (erst versionen.py) oder Bereiche angeben: v1=von:bis,von:bis")
        versionen = [f"{v}=" + ",".join(f"{a}:{e}" for a, e in d["bereiche"]) for v, d in json.loads(b.read_text()).items()]
    if versionen:
        if not args.ziel:
            sys.exit("Für Versionen bitte --ziel <schnitt-ordner> angeben")
        grade_datei = args.grade or (args.ziel / "grade.txt")
        grade = grade_datei.read_text().strip() if grade_datei.exists() else ""
        print(f"Licht: {grade_datei if grade else 'kein grade.txt, ungegradet'}", flush=True)
        versionen_bauen(roh, args.ziel.resolve(), versionen, grade, args.lut.resolve(),
                        (args.ton_von or args.ziel).resolve())


if __name__ == "__main__":
    main()
