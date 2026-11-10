#!/usr/bin/env python3
"""Aus Claudes Take-Auswahl einen sauberen Schnitt machen (Schritt 2).

Eingabe ist der Arbeitsordner von transkript.py mit einer `schnitt.json`, die
Claude geschrieben hat:

  {"clips": [{"von": 12.34, "bis": 15.80, "phrasen": [17, 18], "grund": "..."}],
   "raus":  [{"phrasen": [15, 16], "grund": "..."}]}

`von` ist der Start des ersten behaltenen Wortes, `bis` das Ende des letzten,
beides in Sekunden aus woerter.json.

Unterbefehle:
  kanten  <ordner> [--pause-max 99] [--pause-rest 99]
          Jede Kante in die Stille schieben (nie über das Nachbarwort hinaus),
          auf 30-fps-Frames runden. Schreibt kanten.json. Pausen innerhalb eines
          Takes bleiben (Standard), geschnitten wird nur zwischen Takes. Mit
          kleinerem --pause-max werden Pausen über diesem Wert auf --pause-rest gekürzt.
          Exit 2, wenn eine Kante nicht in Stille liegt.
  ausgabe <ordner> [--master] [--datei <ziel.mp4>]
          schnitt.mp4 per ffmpeg, Ton aus der Originaldatei. Ohne --master eine
          schnelle 720p-Vorschau, mit --master volle Qualität. Für den Weg
          „nur Rohschnitt“ (auch 16:9). iPhone-HDR wird nach bt709 umgerechnet.
"""
from __future__ import annotations

import argparse
import array
import json
import math
import subprocess
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

FPS = config.FPS
VOR = 0.05        # Puffer vor dem ersten Wort
NACH = 0.08       # Puffer nach dem letzten Wort
SUCHE = 0.4       # so weit darf eine Kante wandern
FENSTER = 0.1     # zwei 50-ms-Fenster
LEISE_DB = -35.0
FADE = 0.03


class Audio:
    def __init__(self, pfad: Path):
        with wave.open(str(pfad)) as w:
            self.rate = w.getframerate()
            self.daten = array.array("h", w.readframes(w.getnframes()))

    def db(self, von: float, bis: float) -> float:
        a = max(0, int(von * self.rate))
        b = min(len(self.daten), int(bis * self.rate))
        if b <= a:
            return -120.0
        summe = sum(x * x for x in self.daten[a:b]) / (b - a)
        return 20 * math.log10(math.sqrt(summe) / 32768 + 1e-9)

    def leise(self, von: float, bis: float) -> bool:
        mitte = (von + bis) / 2
        return self.db(von, mitte) < LEISE_DB and self.db(mitte, bis) < LEISE_DB


def laden(ordner: Path, name: str):
    pfad = ordner / name
    if not pfad.exists():
        sys.exit(f"{pfad} fehlt")
    return json.loads(pfad.read_text())


def nachbarn(woerter: list[dict], von: float, bis: float) -> tuple[float, float]:
    """Mitte des Wortes vor `von` und Mitte des Wortes nach `bis`.

    Deepgram dehnt Wörter oft lückenlos aneinander, das Wortende ist deshalb
    keine harte Grenze. Bis zur Wortmitte darf der Pegel die Stille suchen.
    """
    mitte = lambda w: (w["start"] + w["end"]) / 2  # noqa: E731
    vorher = max((mitte(w) for w in woerter if w["end"] <= von + 0.01 and w["start"] < von - 0.01), default=0.0)
    danach = min((mitte(w) for w in woerter if w["start"] >= bis - 0.01 and w["end"] > bis + 0.01), default=1e9)
    return vorher, danach


def kandidaten(ziel: float, unten: float, oben: float) -> list[float]:
    """Frame-Zeitpunkte zwischen unten und oben, nächste zum Ziel zuerst.
    Gleich auf Frames suchen, sonst rundet man eine gute Kante wieder aus der Stille."""
    schritte = range(math.ceil(unten * FPS), math.floor(oben * FPS) + 1)
    return sorted((s / FPS for s in schritte), key=lambda t: abs(t - ziel))


def start_kante(audio: Audio, von: float, erstes: dict, grenze: float) -> tuple[float, bool]:
    """Stille vor dem ersten Wort. Deepgram setzt Wortgrenzen oft daneben, deshalb
    wird zwischen der Mitte des Wortes davor und kurz nach dem Wortstart gesucht."""
    if von <= VOR:
        return 0.0, True
    oben = min(von + 0.05, (erstes["start"] + erstes["end"]) / 2)
    for t in kandidaten(von - VOR, max(von - SUCHE, grenze), oben):
        if audio.leise(t - FENSTER, t):
            return t, True
    return max(von - VOR, (grenze + von) / 2), False


def end_kante(audio: Audio, bis: float, letztes: dict, grenze: float, dauer: float) -> tuple[float, bool]:
    """Stille nach dem letzten Wort, gesucht zwischen der Mitte des letzten Wortes
    und der Mitte des nächsten."""
    if bis + NACH >= dauer:
        return dauer, True
    unten = (letztes["start"] + letztes["end"]) / 2
    for t in kandidaten(bis + NACH, unten, min(bis + SUCHE, grenze)):
        if audio.leise(t, t + FENSTER):
            return t, True
    return min(bis + NACH, (grenze + bis) / 2), False


def pausen_kuerzen(clip: dict, stille: list[dict], innen: tuple[float, float], pause_max: float, rest: float) -> list[dict]:
    """Lange Pausen zwischen zwei behaltenen Wörtern auf `rest` Sekunden kürzen."""
    teile, start = [], clip["von"]
    for s in stille:
        if s["von"] > innen[0] and s["bis"] < innen[1] and s["bis"] - s["von"] > pause_max:
            teile.append({**clip, "von": start, "bis": s["von"] + rest / 2, "endeStill": True})
            start = s["bis"] - rest / 2
            teile[-1]["gekuerzt"] = round(s["bis"] - s["von"] - rest, 2)
    teile.append({**clip, "von": start, "bis": clip["bis"]})
    for i, t in enumerate(teile):
        t["startStill"] = i > 0
        t.setdefault("endeStill", False)
    return teile


def kanten(args) -> None:
    ordner = args.ordner.resolve()
    schnitt = laden(ordner, "schnitt.json")
    woerter = laden(ordner, "woerter.json")
    stille = laden(ordner, "stille.json")
    audio = Audio(ordner / "audio.wav")

    info = laden(ordner, "info.json")
    ergebnis, probleme = [], []
    for nr, clip in enumerate(schnitt["clips"], 1):
        innen = [w for w in woerter if w["start"] >= clip["von"] - 0.01 and w["end"] <= clip["bis"] + 0.01]
        if not innen:
            sys.exit(f"Clip {nr}: keine Wörter zwischen {clip['von']} und {clip['bis']}")
        vorher, danach = nachbarn(woerter, clip["von"], clip["bis"])
        von, start_ok = start_kante(audio, clip["von"], innen[0], vorher)
        bis, ende_ok = end_kante(audio, clip["bis"], innen[-1], min(danach, info["dauer"]), info["dauer"])
        von, bis = max(0.0, von), min(bis, info["dauer"])
        wortspanne = (innen[0]["end"], innen[-1]["start"])
        for teil in pausen_kuerzen({**clip, "von": von, "bis": bis}, stille, wortspanne, args.pause_max, args.pause_rest):
            v = round(teil["von"] * FPS)
            b = round(teil["bis"] * FPS)
            ok_start = teil["startStill"] or (start_ok and audio.leise(v / FPS - FENSTER, v / FPS))
            ok_ende = teil["endeStill"] or (ende_ok and audio.leise(b / FPS, b / FPS + FENSTER))
            eintrag = {
                "clip": nr,
                "von": round(v / FPS, 3),
                "bis": round(b / FPS, 3),
                "vonFrame": v,
                "bisFrame": b,
                "pegelOk": bool(ok_start and ok_ende),
                "phrasen": clip.get("phrasen", []),
                "grund": clip.get("grund", ""),
            }
            if "gekuerzt" in teil:
                eintrag["pauseGekuerzt"] = teil["gekuerzt"]
            ergebnis.append(eintrag)
            if not eintrag["pegelOk"]:
                probleme.append(eintrag)

    for a, b in zip(ergebnis, ergebnis[1:]):
        if b["vonFrame"] < a["bisFrame"]:
            sys.exit(f"Clip {b['clip']} beginnt vor dem Ende von Clip {a['clip']} "
                     f"(Frame {b['vonFrame']} < {a['bisFrame']}). Reihenfolge oder Überlappung in schnitt.json prüfen.")

    frames = sum(e["bisFrame"] - e["vonFrame"] for e in ergebnis)
    (ordner / "kanten.json").write_text(json.dumps(
        {"quelle": info["quelle"], "fps": FPS, "frames": frames, "clips": ergebnis}, ensure_ascii=False, indent=1))
    gekuerzt = sum(e.get("pauseGekuerzt", 0) for e in ergebnis)
    print(f"{len(ergebnis)} Clips, {frames / FPS:.1f} s statt {info['dauer']:.1f} s, Pausen um {gekuerzt:.1f} s gekürzt")
    for e in probleme:
        print(f"  Kante nicht in Stille: Clip {e['clip']} [{e['von']:.2f}–{e['bis']:.2f}] {e['phrasen']}")
    if probleme:
        sys.exit(2)


def hdr_filter(quelle: str) -> str:
    """iPhone-HDR (HLG) per LUT nach bt709, sonst nichts."""
    if not config.ist_hlg(Path(quelle)):
        return ""
    lut = config.ASSETS / "hlg709.cube"
    return (f",scale=in_color_matrix=bt2020:in_range=tv,format=gbrp16le,lut3d={lut},format=yuv420p,"
            "setparams=range=tv:color_primaries=bt709:color_trc=bt709:colorspace=bt709")


def mp4_bauen(ordner: Path, kanten_daten: dict, master: bool, ausgabe: Path | None = None) -> None:
    clips = kanten_daten["clips"]
    teile, labels = [], ""
    farbe = hdr_filter(kanten_daten["quelle"])
    for i, c in enumerate(clips):
        dauer = (c["bisFrame"] - c["vonFrame"]) / FPS
        skal = "" if master else ",scale=-2:720"
        # Zeitbasiert schneiden und danach auf 30 fps takten: hält auch bei variabler Bildrate.
        teile.append(
            f"[0:v]trim=start={c['vonFrame'] / FPS:.6f}:end={c['bisFrame'] / FPS:.6f},setpts=PTS-STARTPTS,"
            f"fps={FPS}{farbe}{skal}[v{i}];"
            f"[0:a]atrim=start={c['vonFrame'] / FPS}:end={c['bisFrame'] / FPS},asetpts=PTS-STARTPTS,"
            f"afade=t=in:st=0:d={FADE},afade=t=out:st={max(0, dauer - FADE):.3f}:d={FADE}[a{i}]"
        )
        labels += f"[v{i}][a{i}]"
    graph = ";".join(teile) + f";{labels}concat=n={len(clips)}:v=1:a=1[v][a]"
    graph_datei = ordner / "filter.txt"
    graph_datei.write_text(graph)
    ausgabe = ausgabe or ordner / "schnitt.mp4"
    qualitaet = ["-crf", "16", "-preset", "medium", "-b:a", "192k"] if master else ["-crf", "23", "-preset", "veryfast", "-b:a", "128k"]
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", kanten_daten["quelle"], "-filter_complex_script", str(graph_datei),
         "-map", "[v]", "-map", "[a]", "-r", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p", *qualitaet,
         "-c:a", "aac", "-movflags", "+faststart", str(ausgabe)],
        check=True,
    )
    gezaehlt = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v", "-count_frames", "-show_entries",
         "stream=nb_read_frames", "-of", "csv=p=0", str(ausgabe)],
        capture_output=True, text=True,
    ).stdout.strip()
    soll = kanten_daten["frames"]
    print(f"{ausgabe.name}: {gezaehlt} Frames, Soll {soll}")
    if config.first_int(gezaehlt) != soll:
        sys.exit("Framezahl weicht ab")


def ausgabe(args) -> None:
    ordner = args.ordner.resolve()
    kanten_daten = laden(ordner, "kanten.json")
    mp4_bauen(ordner, kanten_daten, args.master, args.datei.resolve() if args.datei else None)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    unter = ap.add_subparsers(dest="befehl", required=True)
    k = unter.add_parser("kanten")
    k.add_argument("ordner", type=Path)
    k.add_argument("--pause-max", type=float, default=99.0, help="Pausen über diesem Wert kürzen (Standard: keine)")
    k.add_argument("--pause-rest", type=float, default=99.0, help="Restlänge gekürzter Pausen")
    k.set_defaults(func=kanten)
    a = unter.add_parser("ausgabe")
    a.add_argument("ordner", type=Path)
    a.add_argument("--master", action="store_true", help="volle Qualität statt 720p-Vorschau")
    a.add_argument("--datei", type=Path, help="Zieldatei (Standard: <ordner>/schnitt.mp4)")
    a.set_defaults(func=ausgabe)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
