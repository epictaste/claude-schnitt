"""zone.py: finding the top edge of a subtitle box without an image library."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from conftest import SCRIPTS, needs_ffmpeg  # noqa: E402

import zone  # noqa: E402

WIDTH = 320
HEIGHT = 568


def frame_with_box(box_top: int, box_height: int = 80, background: int = 200) -> bytes:
    """A bright grayscale frame with one dark band, as raw bytes."""
    buffer = bytearray([background] * (WIDTH * HEIGHT))
    for y in range(box_top, min(HEIGHT, box_top + box_height)):
        for x in range(WIDTH):
            buffer[y * WIDTH + x] = 10
    return bytes(buffer)


def test_finds_the_top_edge_of_a_dark_band():
    assert zone.find_box_top(frame_with_box(400), WIDTH, HEIGHT) == 400


def test_ignores_a_single_dark_line():
    buffer = bytearray([200] * (WIDTH * HEIGHT))
    for x in range(WIDTH):
        buffer[300 * WIDTH + x] = 0
    assert zone.find_box_top(bytes(buffer), WIDTH, HEIGHT) is None


def test_ignores_dark_rows_outside_the_scan_band():
    # A dark band in the top tenth is a letterbox or a graphic, not a subtitle.
    assert zone.find_box_top(frame_with_box(20), WIDTH, HEIGHT) is None


def test_no_box_on_an_even_frame():
    assert zone.find_box_top(bytes([200] * (WIDTH * HEIGHT)), WIDTH, HEIGHT) is None


def test_row_means_rejects_a_short_buffer():
    try:
        zone.row_means(b"\x00" * 10, WIDTH, HEIGHT)
    except ValueError as exc:
        assert "expected at least" in str(exc)
    else:
        raise AssertionError("a truncated frame must not pass silently")


def test_consensus_takes_the_highest_clustered_edge():
    # Two-line subtitles push the edge up; that is the one the zone must respect.
    assert zone.consensus([880, 878, 812, 879]) == 812


def test_consensus_drops_an_outlier():
    assert zone.consensus([880, 878, 200, 879]) == 878


def test_consensus_without_samples():
    assert zone.consensus([]) is None


@needs_ffmpeg
def test_measures_a_real_clip(tmp_path: Path):
    video = tmp_path / "boxed.mp4"
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-nostdin", "-y",
            "-f", "lavfi", "-i", f"color=c=gray:s={WIDTH}x{HEIGHT}:rate=30:duration=3",
            "-vf", "drawbox=x=0:y=400:w=320:h=80:color=black@1:t=fill",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video),
        ],
        check=True,
        capture_output=True,
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "zone.py"), str(video), "--json"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["method"] == "subtitle-box"
    assert abs(payload["boxTop"] - 400) <= 2
    assert payload["zoneHeight"] == payload["boxTop"] - payload["margin"] - (
        (payload["boxTop"] - payload["margin"]) % 2
    )
    assert payload["zoneHeight"] % 2 == 0


@needs_ffmpeg
def test_falls_back_to_half_the_frame(tmp_path: Path):
    video = tmp_path / "plain.mp4"
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-nostdin", "-y",
            "-f", "lavfi", "-i", f"color=c=gray:s={WIDTH}x{HEIGHT}:rate=30:duration=2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video),
        ],
        check=True,
        capture_output=True,
    )
    measured = zone.measure(video, samples=3)
    assert measured["method"] == "fallback-half-frame"
    assert measured["zoneHeight"] == HEIGHT // 2
