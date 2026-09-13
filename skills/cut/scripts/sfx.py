#!/usr/bin/env python3
"""Synthesize the six UI sounds the animation zone uses.

No sound library, no downloads, no licensing question: ffmpeg generates every
sound from sine tones and filtered noise, and each one is normalized to a fixed
peak so the mix stays predictable. They are deliberately small and dry, and they
sit about 10 dB under the voice in the final mix.

  click   hard scene change, a stamp landing
  tick    a list row, a check mark
  pop     a card or badge appearing
  whoosh  something flying in
  ding    success
  type    one keystroke, used in rows for typing reveals

Usage:
  sfx.py path/to/project/public          # writes public/sfx/*.wav
  sfx.py path/to/project/public --force  # rebuild even if they exist
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import config  # noqa: E402

SOUNDS = ("click", "tick", "pop", "whoosh", "ding", "type")

#: name -> (target peak in dBFS, ffmpeg input and filter arguments)
RECIPES: dict[str, tuple[int, list[str]]] = {
    # Short 1800 Hz burst with an exponential decay plus a noise transient.
    "click": (
        -18,
        [
            "-f", "lavfi", "-i", "sine=f=1800:d=0.014:r=48000",
            "-f", "lavfi", "-i", "anoisesrc=d=0.004:c=white:a=0.7:r=48000:seed=11",
            "-filter_complex",
            "[0:a]afade=t=out:st=0:d=0.014:curve=exp[t];"
            "[1:a]highpass=f=2500,afade=t=out:st=0:d=0.004[n];"
            "[t][n]amix=inputs=2:normalize=0,apad=whole_dur=0.05",
        ],
    ),
    # Quieter, higher, shorter. For list rows and table lines.
    "tick": (
        -24,
        [
            "-f", "lavfi", "-i", "sine=f=3200:d=0.006:r=48000",
            "-af", "afade=t=out:st=0:d=0.006:curve=exp,apad=whole_dur=0.04",
        ],
    ),
    # Filtered noise under a bell envelope. The phaser gives it movement.
    "whoosh": (
        -22,
        [
            "-f", "lavfi", "-i", "anoisesrc=d=0.25:c=pink:a=1:r=48000:seed=22",
            "-af",
            "highpass=f=400,lowpass=f=5200,"
            "aphaser=in_gain=0.6:out_gain=0.9:delay=3:decay=0.5:speed=2,"
            "afade=t=in:st=0:d=0.09:curve=exp,afade=t=out:st=0.1:d=0.15",
        ],
    ),
    # Sine sweep from 320 Hz to 1200 Hz in 70 ms, then cut.
    "pop": (
        -18,
        [
            "-f", "lavfi", "-i", "aevalsrc='sin(2*PI*(320*t+6285*t*t))':d=0.07:s=48000",
            "-af", "afade=t=out:st=0.03:d=0.04:curve=exp,apad=whole_dur=0.09",
        ],
    ),
    # Two short sine tones (880 Hz, then 1320 Hz) for check marks and success.
    "ding": (
        -18,
        [
            "-f", "lavfi", "-i", "sine=f=880:d=0.16:r=48000",
            "-f", "lavfi", "-i", "sine=f=1320:d=0.16:r=48000",
            "-filter_complex",
            "[0:a]afade=t=out:st=0:d=0.16:curve=exp[a];"
            "[1:a]afade=t=out:st=0:d=0.16:curve=exp,adelay=55|55[b];"
            "[a][b]amix=inputs=2:normalize=0,apad=whole_dur=0.22",
        ],
    ),
    # One dry keystroke.
    "type": (
        -26,
        [
            "-f", "lavfi", "-i", "anoisesrc=d=0.004:c=white:a=0.8:r=48000:seed=33",
            "-f", "lavfi", "-i", "sine=f=1200:d=0.006:r=48000",
            "-filter_complex",
            "[0:a]highpass=f=1500,afade=t=out:st=0:d=0.004[n];"
            "[1:a]afade=t=out:st=0:d=0.006:curve=exp,volume=0.5[s];"
            "[n][s]amix=inputs=2:normalize=0,apad=whole_dur=0.035",
        ],
    ),
}

PEAK_PATTERN = re.compile(r"max_volume:\s*(-?\d+(?:\.\d+)?) dB")


def measure_peak(path: Path) -> float:
    """Peak level of a file in dBFS, read from ffmpeg's volumedetect filter."""
    import subprocess

    result = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    match = PEAK_PATTERN.search(result.stderr or "")
    if not match:
        raise config.MediaError(f"could not measure the peak level of {path.name}")
    return float(match.group(1))


def build_sound(name: str, target_db: int, args: list[str], out_dir: Path, tmp: Path) -> Path:
    raw = tmp / f"{name}-raw.wav"
    config.run(["ffmpeg", "-v", "error", "-y", *args, str(raw)], f"synthesizing {name}")
    gain = target_db - measure_peak(raw)
    out_path = out_dir / f"{name}.wav"
    config.run(
        [
            "ffmpeg", "-v", "error", "-y", "-i", str(raw),
            "-af", f"volume={gain:.2f}dB",
            "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "1",
            str(out_path),
        ],
        f"normalizing {name}",
    )
    return out_path


def generate(public_dir: Path, force: bool = False) -> list[Path]:
    """Write all six sounds into <public_dir>/sfx. Existing files are kept."""
    out_dir = Path(public_dir) / "sfx"
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    with TemporaryDirectory(prefix="cut-sfx-") as tmp_name:
        tmp = Path(tmp_name)
        for name in SOUNDS:
            target_db, args = RECIPES[name]
            out_path = out_dir / f"{name}.wav"
            if out_path.exists() and not force:
                continue
            written.append(build_sound(name, target_db, args, out_dir, tmp))
    return written


def is_complete(public_dir: Path) -> bool:
    sfx_dir = Path(public_dir) / "sfx"
    return all((sfx_dir / f"{name}.wav").exists() for name in SOUNDS)


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthesize the six UI sounds with ffmpeg.")
    parser.add_argument("public_dir", type=Path, help="the project's public/ directory")
    parser.add_argument("--force", action="store_true", help="rebuild sounds that already exist")
    args = parser.parse_args()

    try:
        written = generate(args.public_dir, args.force)
    except config.MediaError as exc:
        print(f"[cut] {exc}", file=sys.stderr)
        return 1

    target = Path(args.public_dir) / "sfx"
    if written:
        print(f"[cut] wrote {len(written)} sounds to {target}")
    else:
        print(f"[cut] all six sounds already in {target} (use --force to rebuild)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
