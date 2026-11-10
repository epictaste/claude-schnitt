"""Gemeinsame Test-Helfer: Skript-Ordner auf den Importpfad, synthetische Videos und Tonspuren."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL = REPO_ROOT / "skills" / "schnitt"
SCRIPTS = SKILL / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

FPS = 30


def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


needs_ffmpeg = pytest.mark.skipif(not has_ffmpeg(), reason="ffmpeg und ffprobe nötig")
needs_zsh = pytest.mark.skipif(shutil.which("zsh") is None, reason="zsh nötig")


def ton_ausdruck(toene: list[tuple[float, float]], pegel: float = 0.5, rauschen: float = 0.001) -> str:
    """aevalsrc-Ausdruck: 440-Hz-Ton in den Bereichen `toene`, sonst leises Rauschen (keine digitale Stille)."""
    an = "+".join(f"between(t,{a},{b})" for a, b in toene) or "0"
    return f"{pegel}*sin(2*PI*440*t)*({an})+{rauschen}*(2*random(0)-1)"


def synth_video(path: Path, frames: int, width: int = 320, height: int = 568, fps: int = FPS,
                toene: list[tuple[float, float]] | None = None, quelle: str = "testsrc2") -> Path:
    """Kurzes Testvideo mit bewegtem Bild. Ton: Dauerton, oder mit `toene` nur in diesen Bereichen (Sekunden)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    dauer = frames / fps
    ton = ton_ausdruck(toene) if toene is not None else ton_ausdruck([(0, dauer)])
    subprocess.run(
        ["ffmpeg", "-v", "error", "-nostdin", "-y",
         "-f", "lavfi", "-i", f"{quelle}=size={width}x{height}:rate={fps}:duration={dauer}",
         "-f", "lavfi", "-i", f"aevalsrc='{ton}':s=48000:d={dauer}",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-frames:v", str(frames),
         "-c:a", "aac", "-b:a", "128k", "-shortest", str(path)],
        check=True, capture_output=True,
    )
    return path


def schreibe_wav(pfad: Path, sekunden: float, bloecke: list[tuple[float, float, float]], sr: int = 16000,
                 rauschen_db: float = -80.0) -> Path:
    """Mono-WAV (16 bit) mit Sinus-Blöcken (von, bis, Pegel in dBFS) über leisem Rauschen."""
    import numpy as np

    rng = np.random.default_rng(7)
    n = int(sekunden * sr)
    t = np.arange(n) / sr
    x = rng.uniform(-1, 1, n) * 10 ** (rauschen_db / 20)
    for a, b, db in bloecke:
        m = (t >= a) & (t < b)
        x[m] += np.sin(2 * np.pi * 440 * t[m]) * 10 ** (db / 20) * np.sqrt(2)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(pfad), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
    return pfad


def rohschnitt_ordner(ordner: Path, video: Path, woerter: list[dict], clips: list[dict]) -> Path:
    """Rohschnitt-Ordner wie nach transkript.py, aber ohne Deepgram: Wörter werden vorgegeben."""
    import transkript

    ordner.mkdir(parents=True, exist_ok=True)
    info = transkript.video_info(video)
    (ordner / "info.json").write_text(json.dumps(info))
    transkript.audio_extrahieren(video, ordner / "audio.wav")
    (ordner / "woerter.json").write_text(json.dumps(woerter, ensure_ascii=False))
    (ordner / "stille.json").write_text(json.dumps(transkript.stille_finden(ordner / "audio.wav")))
    (ordner / "schnitt.json").write_text(json.dumps({"clips": clips, "raus": []}))
    return ordner


#: Fünf „Wörter“ als Tonblöcke, dazwischen Stille.
WORT_BLOECKE = [(0.5, 1.5), (2.0, 3.0), (4.0, 5.0), (6.0, 7.0), (8.0, 9.0)]
WOERTER = [{"wort": f"Wort{i + 1}.", "start": a, "end": b} for i, (a, b) in enumerate(WORT_BLOECKE)]


@pytest.fixture
def roh(tmp_path: Path) -> Path:
    """Rohschnitt-Ordner aus einem 10-s-Testvideo, jeder Tonblock ein eigener Clip."""
    video = synth_video(tmp_path / "quelle.mp4", 300, toene=WORT_BLOECKE)
    clips = [{"von": w["start"], "bis": w["end"], "phrasen": [i + 1]} for i, w in enumerate(WOERTER)]
    return rohschnitt_ordner(tmp_path / "schnitt-quelle" / "rohschnitt" / "quelle", video, WOERTER, clips)
