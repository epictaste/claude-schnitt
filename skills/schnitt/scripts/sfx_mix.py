#!/usr/bin/env python3
"""Sound-Standard auf die Tonspur einer Version legen (Schritt 6).

Hook: Ein Riser steigt über Satz 1 und hat seine Spitze genau auf dem ersten
harten Schnitt (SATZ2), 40 ms danach ein Whoosh. Body: die Effekte aus den
Szenen-Cues (click, tick, pop, whoosh, type), alle mit demselben Pegel.
Ketten (mindestens 3 Effekte mit höchstens 0,6 s Abstand, etwa Tippen) bleiben
ganz, einzelne Effekte höchstens einer pro 0,8 s. Kein Bestätigungs-Ding.
Alle Sounds erzeugt sfx.py per ffmpeg.

Aufruf:
  sfx_mix.py <stimme> <cues.json> <schnitt_s> <aus.wav> [--riser-db -15] [--whoosh-db -11]
             [--riser-anteil 0.75] [--pop-als-click] [--ohne-hook]

  stimme     Ton der Version ohne Effekte, z. B. schnitt/v1-neu.mp4 (jede Datei, die ffmpeg liest)
  cues.json  [{"t": Sekunden, "rolle": "click|tick|pop|whoosh|type", "gain": 0..1}], aus `npm run -s cues -- v1`
  schnitt_s  erster harter Schnitt in Sekunden (SATZ2 / 30 aus meta.json)
  aus.wav    Ergebnis, 48 kHz Stereo, 24 bit. bauen.sh nimmt es per --ton-video.

Pegel: Effekt-Spitze -17 dBFS bei gain 0,45, der Standard-gain 0,25 liegt also
rund 5 dB darunter. Braucht numpy (Python-Umgebung aus setup.py).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sfx  # noqa: E402

SR = sfx.SR
BASIS = {"click": -17, "tick": -17, "pop": -17, "whoosh": -17, "type": -19, "ding": -19}
AUS = {"ding"}
KETTE_ABSTAND, KETTE_MIN, MIN_ABSTAND = 0.6, 3, 0.8
GAIN_BEZUG = 0.45


def lade(pfad: Path, kanaele: int = 1) -> np.ndarray:
    cmd = ["ffmpeg", "-v", "error", "-i", str(pfad), "-ac", str(kanaele), "-ar", str(SR), "-f", "f32le", "-"]
    y = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).copy()
    return y.reshape(-1, kanaele) if kanaele > 1 else y


def norm(y: np.ndarray, db: float) -> np.ndarray:
    return y / (np.abs(y).max() + 1e-12) * 10 ** (db / 20)


def spitze_s(y: np.ndarray, fenster: float = 0.03) -> float:
    e = np.abs(y).max(axis=1) if y.ndim == 2 else np.abs(y)
    w = int(fenster * SR)
    k = max(1, len(e) // w)
    return float(np.argmax(e[:k * w].reshape(k, w).max(axis=1)) * w / SR)


def effekt(name: str, tmp: Path, variante: int = 0, dauer: float | None = None) -> np.ndarray:
    """Effekt erzeugen (Spitze -1 dBFS) und als Mono-Array laden."""
    pfad = tmp / f"{name}-{variante}-{dauer or 0:.3f}.wav"
    if not pfad.exists():
        sfx.bauen(name, pfad, -1.0, variante, dauer)
    return lade(pfad).astype(np.float64)


def ausduennen(cues: list[dict]) -> list[dict]:
    """Ketten bleiben ganz, Einzel-Effekte höchstens einer pro MIN_ABSTAND (lautere zuerst)."""
    roh = sorted([dict(c) for c in cues if c["rolle"] not in AUS and c["rolle"] in BASIS], key=lambda c: c["t"])
    # Derselbe Effekt mehrfach im selben Moment wäre nur lauter, nicht reicher: einer bleibt.
    cues = []
    for c in roh:
        if not any(d["rolle"] == c["rolle"] and abs(d["t"] - c["t"]) < 0.02 for d in cues[-3:]):
            cues.append(c)
    if not cues:
        return []
    ketten, akt = [], [cues[0]]
    for c in cues[1:]:
        if c["t"] - akt[-1]["t"] <= KETTE_ABSTAND:
            akt.append(c)
        else:
            ketten.append(akt)
            akt = [c]
    ketten.append(akt)
    fest, einzeln = [], []
    for k in ketten:
        if len(k) >= KETTE_MIN:
            # Eine Kette aus Klicks und Ticks ohne Tippen klingt wie Nachrichten: Ticks werden zu Pops.
            nachricht = any(c["rolle"] in ("click", "tick") for c in k) and not any(c["rolle"] == "type" for c in k)
            for c in k:
                if nachricht and c["rolle"] == "tick":
                    c["rolle"] = "pop"
                fest.append(c)
        else:
            einzeln += k
    behalten = list(fest)
    for c in sorted(einzeln, key=lambda c: -c["gain"]):
        if all(abs(c["t"] - b["t"]) >= MIN_ABSTAND for b in behalten):
            behalten.append(c)
    return sorted(behalten, key=lambda c: c["t"])


def mischen(stimme: Path, cues: list[dict], schnitt: float, aus: Path, riser_db: float = -15.0, whoosh_db: float = -11.0,
            riser_anteil: float = 0.75, pop_als_click: bool = False, mit_hook: bool = True) -> dict:
    ton = lade(stimme, kanaele=2).astype(np.float64)
    spur = np.zeros(len(ton))
    cues = ausduennen(cues)
    with tempfile.TemporaryDirectory(prefix="schnitt-mix-") as t:
        tmp = Path(t)
        zaehler: dict[str, int] = {}
        for c in cues:
            r = "click" if (pop_als_click and c["rolle"] == "pop") else c["rolle"]
            k = zaehler.get(r, 0)
            zaehler[r] = k + 1
            s = effekt(r, tmp, k % sfx.TYPE_VARIANTEN if r == "type" else 0)
            g = 10 ** (BASIS[r] / 20) * c["gain"] / GAIN_BEZUG
            a = int(c["t"] * SR)
            b = min(len(spur), a + len(s))
            if 0 <= a < len(spur):
                spur[a:b] += s[:b - a] * g
        hook = mit_hook and 0.5 <= schnitt < len(ton) / SR
        if hook:
            # Riser: steigt über `riser_anteil` von Satz 1, Spitze auf dem Schnitt, 60 ms Ausklang
            laenge = max(0.4, min(schnitt, schnitt * riser_anteil))
            ry = effekt("riser", tmp, dauer=laenge + 0.06)
            n_aus = int(0.06 * SR)
            ry[-n_aus:] *= np.linspace(1, 0, n_aus)
            ry = norm(ry, riser_db)
            start = int(schnitt * SR) - int(spitze_s(ry) * SR)
            ry = ry[max(0, -start):]
            start = max(0, start)
            n = min(len(ry), len(spur) - start)
            spur[start:start + n] += ry[:n]
            # Whoosh: Spitze 40 ms nach dem Schnitt
            wy = norm(effekt("whoosh", tmp), whoosh_db)
            s0 = int((schnitt + 0.04 - spitze_s(wy)) * SR)
            wy = wy[max(0, -s0):]
            s0 = max(0, s0)
            n = min(len(wy), len(spur) - s0)
            spur[s0:s0 + n] += wy[:n]
    mix = ton + np.repeat(spur[:, None], 2, axis=1)
    mix *= min(1.0, 10 ** (-1 / 20) / (np.abs(mix).max() + 1e-12))
    aus.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                    "-c:a", "pcm_s24le", str(aus)], input=mix.astype(np.float32).tobytes(), check=True)
    zahl = {r: sum(c["rolle"] == r for c in cues) for r in BASIS if r not in AUS}
    spitze = 20 * np.log10(np.abs(mix).max() + 1e-12)
    print("Effekte nach Ausdünnen:", zahl, "gesamt", len(cues), "| Hook:", "Riser + Whoosh" if hook else "keiner")
    print(f"Spitze Mix {spitze:.1f} dBFS -> {aus}")
    return {"effekte": zahl, "hook": hook, "spitze_db": round(float(spitze), 1)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stimme", type=Path)
    ap.add_argument("cues", type=Path)
    ap.add_argument("schnitt", type=float)
    ap.add_argument("aus", type=Path)
    ap.add_argument("--riser-db", type=float, default=-15.0)
    ap.add_argument("--whoosh-db", type=float, default=-11.0)
    ap.add_argument("--riser-anteil", type=float, default=0.75, help="Anteil von Satz 1, über den der Riser steigt")
    ap.add_argument("--pop-als-click", action="store_true", help="statt des weichen Swish einen Klick nehmen")
    ap.add_argument("--ohne-hook", action="store_true", help="keinen Riser und keinen Whoosh am Hook")
    args = ap.parse_args()
    cues = json.loads(args.cues.read_text()) if args.cues.exists() else []
    mischen(args.stimme, cues, args.schnitt, args.aus, args.riser_db, args.whoosh_db, args.riser_anteil,
            args.pop_als_click, not args.ohne_hook)


if __name__ == "__main__":
    main()
