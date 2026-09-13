"""Shared test setup: put the skill's scripts on the import path."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "skills" / "cut" / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


needs_ffmpeg = pytest.mark.skipif(not has_ffmpeg(), reason="ffmpeg and ffprobe are required")


def synth_video(path: Path, frames: int, width: int = 320, height: int = 568, fps: int = 30) -> Path:
    """A short silent-audio test clip with a moving picture, built by ffmpeg."""
    path.parent.mkdir(parents=True, exist_ok=True)
    duration = frames / fps
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-nostdin", "-y",
            "-f", "lavfi", "-i", f"testsrc=size={width}x{height}:rate={fps}:duration={duration}",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-frames:v", str(frames),
            "-c:a", "aac", "-b:a", "64k", "-shortest",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    return path
