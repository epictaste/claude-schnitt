#!/usr/bin/env python3
"""Sound-Effekte per ffmpeg erzeugen. Keine Sound-Bibliothek, kein Download, keine Lizenzfrage.

Jeder Effekt entsteht aus Sinustönen und gefiltertem Rauschen und wird auf eine
feste Spitze normalisiert, damit die Mischung berechenbar bleibt:

  click   harter Szenenwechsel, etwas landet
  tick    Listenzeile, Haken
  pop     Karte oder Badge erscheint (weicher Swish, kein greller Pop)
  whoosh  etwas fliegt rein, auch der Whoosh direkt nach dem ersten harten Schnitt
  ding    Erfolg (sfx_mix.py lässt ihn standardmäßig weg)
  type    ein Tastenanschlag, für Tipp-Animationen (5 Varianten)
  riser   steigt über Satz 1 bis zum ersten harten Schnitt, Länge frei wählbar

Aufruf:
  sfx.py <ordner>          # schreibt <ordner>/sfx/*.wav
  sfx.py <ordner> --force  # vorhandene neu bauen
sfx_mix.py nutzt dieselben Rezepte direkt.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

SR = 48000
SOUNDS = ("click", "tick", "pop", "whoosh", "ding", "type", "riser")
TYPE_VARIANTEN = 5
PEAK_PATTERN = re.compile(r"max_volume:\s*(-?\d+(?:\.\d+)?) dB")


def rezept(name: str, variante: int = 0, dauer: float | None = None) -> list[str]:
    """ffmpeg-Eingaben und Filter für einen Effekt. `variante` ändert Rauschen und Tonhöhe leicht."""
    seed = 11 + 7 * variante
    if name == "click":
        return ["-f", "lavfi", "-i", f"sine=f=1800:d=0.014:r={SR}",
                "-f", "lavfi", "-i", f"anoisesrc=d=0.004:c=white:a=0.7:r={SR}:seed={seed}",
                "-filter_complex", "[0:a]afade=t=out:st=0:d=0.014:curve=exp[t];"
                "[1:a]highpass=f=2500,afade=t=out:st=0:d=0.004[n];[t][n]amix=inputs=2:normalize=0,apad=whole_dur=0.05"]
    if name == "tick":
        return ["-f", "lavfi", "-i", f"sine=f=3200:d=0.006:r={SR}",
                "-af", "afade=t=out:st=0:d=0.006:curve=exp,apad=whole_dur=0.04"]
    if name == "pop":
        # Weicher Swish: kurzes rosa Rauschen, Bandpass, Glockenkurve. Tut nicht weh, auch zehnmal im Video.
        return ["-f", "lavfi", "-i", f"anoisesrc=d=0.16:c=pink:a=1:r={SR}:seed={seed}",
                "-af", "highpass=f=700,lowpass=f=4200,afade=t=in:st=0:d=0.06:curve=qsin,afade=t=out:st=0.06:d=0.10:curve=qsin"]
    if name == "whoosh":
        return ["-f", "lavfi", "-i", f"anoisesrc=d=0.6:c=pink:a=1:r={SR}:seed={seed + 1}",
                "-af", "highpass=f=300,lowpass=f=6000,aphaser=in_gain=0.6:out_gain=0.9:delay=3:decay=0.5:speed=1.5,"
                "afade=t=in:st=0:d=0.22:curve=exp,afade=t=out:st=0.22:d=0.38:curve=qsin"]
    if name == "ding":
        return ["-f", "lavfi", "-i", f"sine=f=880:d=0.16:r={SR}", "-f", "lavfi", "-i", f"sine=f=1320:d=0.16:r={SR}",
                "-filter_complex", "[0:a]afade=t=out:st=0:d=0.16:curve=exp[a];"
                "[1:a]afade=t=out:st=0:d=0.16:curve=exp,adelay=55|55[b];[a][b]amix=inputs=2:normalize=0,apad=whole_dur=0.22"]
    if name == "type":
        ton = 1000 + 120 * variante
        return ["-f", "lavfi", "-i", f"anoisesrc=d=0.006:c=white:a=0.8:r={SR}:seed={seed}",
                "-f", "lavfi", "-i", f"sine=f={ton}:d=0.008:r={SR}",
                "-filter_complex", "[0:a]highpass=f=1500,afade=t=out:st=0:d=0.006[n];"
                "[1:a]afade=t=out:st=0:d=0.008:curve=exp,volume=0.5[s];[n][s]amix=inputs=2:normalize=0,apad=whole_dur=0.04"]
    if name == "riser":
        d = max(0.4, dauer or 2.0)
        # Ton gleitet von 180 auf 1400 Hz, Rauschen und Ton werden zum Ende quadratisch lauter, Spitze am Ende.
        chirp = f"(t/{d})^2*(0.6*sin(2*PI*(180*t+{(1400 - 180) / (2 * d):.3f}*t*t))+0.5*(2*random(0)-1))"
        return ["-f", "lavfi", "-i", f"aevalsrc='{chirp}':d={d:.3f}:s={SR}",
                "-af", "highpass=f=150,lowpass=f=9000,afade=t=in:st=0:d=0.25"]
    raise ValueError(f"unbekannter Effekt: {name}")


def measure_peak(pfad: Path) -> float:
    """Spitzenpegel in dBFS (ffmpeg volumedetect)."""
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", str(pfad), "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = PEAK_PATTERN.search(r.stderr or "")
    if not m:
        raise config.MediaError(f"Spitzenpegel von {pfad.name} nicht messbar")
    return float(m.group(1))


def bauen(name: str, ziel: Path, ziel_db: float = -1.0, variante: int = 0, dauer: float | None = None) -> Path:
    """Effekt als 48-kHz-Mono-WAV mit Spitze `ziel_db` schreiben."""
    ziel.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="schnitt-sfx-") as t:
        roh = Path(t) / "roh.wav"
        config.run(["ffmpeg", "-v", "error", "-y", *rezept(name, variante, dauer), "-ac", "1", str(roh)], f"{name} erzeugen")
        gain = ziel_db - measure_peak(roh)
        config.run(["ffmpeg", "-v", "error", "-y", "-i", str(roh), "-af", f"volume={gain:.2f}dB",
                    "-c:a", "pcm_s16le", "-ar", str(SR), "-ac", "1", str(ziel)], f"{name} normalisieren")
    return ziel


def generate(ordner: Path, force: bool = False) -> list[Path]:
    """Alle Effekte nach <ordner>/sfx schreiben. Vorhandene bleiben, außer mit force."""
    aus = Path(ordner) / "sfx"
    geschrieben = []
    for name in SOUNDS:
        varianten = TYPE_VARIANTEN if name == "type" else 1
        for v in range(varianten):
            ziel = aus / (f"{name}-{v + 1}.wav" if varianten > 1 else f"{name}.wav")
            if ziel.exists() and not force:
                continue
            geschrieben.append(bauen(name, ziel, variante=v))
    return geschrieben


def is_complete(ordner: Path) -> bool:
    aus = Path(ordner) / "sfx"
    namen = [f"{n}.wav" for n in SOUNDS if n != "type"] + [f"type-{v + 1}.wav" for v in range(TYPE_VARIANTEN)]
    return all((aus / n).exists() for n in namen)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ordner", type=Path)
    ap.add_argument("--force", action="store_true", help="vorhandene Effekte neu bauen")
    args = ap.parse_args()
    try:
        geschrieben = generate(args.ordner, args.force)
    except config.MediaError as exc:
        print(f"[schnitt] {exc}", file=sys.stderr)
        return 1
    ziel = Path(args.ordner) / "sfx"
    print(f"[schnitt] {len(geschrieben)} Effekte nach {ziel}" if geschrieben
          else f"[schnitt] alle Effekte schon in {ziel} (--force baut neu)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
