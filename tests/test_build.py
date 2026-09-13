"""build.py: reading the version layout, refusing a mismatch, contact sheets."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from conftest import needs_ffmpeg, synth_video  # noqa: E402

import build  # noqa: E402
import config  # noqa: E402

TIMING = """
export const VERSIONS: Record<number, Version> = {
	1: {cut: 'v1.mp4', layout: [{part: 'hookA', frames: 103}, {part: 'body', frames: 230}]},
	2: {cut: 'v2.mp4', layout: [{part: 'hookB', frames: 135}, {part: 'body', frames: 230}]},
};

export const SFX_READY = true;
"""


def test_parses_a_layout_per_version():
    versions = build.parse_versions(TIMING)
    assert versions == {
        1: {"cut": "v1.mp4", "frames": 333},
        2: {"cut": "v2.mp4", "frames": 365},
    }


def test_versions_of_different_lengths_stay_apart():
    versions = build.parse_versions(TIMING)
    assert versions[1]["frames"] != versions[2]["frames"]


def test_a_comment_mentioning_versions_is_not_the_declaration():
    # The template header says "cut.py -> VERSIONS" in a comment. Searching for
    # the bare word landed there and parsed the wrong braces.
    text = "// fill VERSIONS from cut.py\nexport const ZONE = {width: 1080, height: 855};\n" + TIMING
    assert build.parse_versions(text) == {
        1: {"cut": "v1.mp4", "frames": 333},
        2: {"cut": "v2.mp4", "frames": 365},
    }


def test_parsing_an_unreadable_block_returns_nothing():
    assert build.parse_versions("no versions here") == {}
    assert build.parse_versions("export const VERSIONS") == {}


def test_read_version_falls_back_when_timing_is_missing(tmp_path: Path):
    assert build.read_version(tmp_path, 1) == (None, "cut.mp4")


def test_read_version_reads_the_project(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "timing.ts").write_text(TIMING, encoding="utf-8")
    assert build.read_version(tmp_path, 2) == (365, "v2.mp4")


def test_matching_frame_counts_pass():
    build.verify_frames(1, cut_frames=333, zone_frames=333, declared=333)
    # A project whose timing.ts could not be parsed still builds.
    build.verify_frames(1, cut_frames=333, zone_frames=333, declared=None)


def test_a_short_zone_render_stops_the_build():
    # The composite uses shortest=1, so this would have produced a video that
    # ends early instead of an error.
    with pytest.raises(config.MediaError, match="rendered zone has 300"):
        build.verify_frames(1, cut_frames=333, zone_frames=300, declared=333)


def test_a_layout_that_disagrees_with_the_cut_stops_the_build():
    with pytest.raises(config.MediaError, match="adds up to 365"):
        build.verify_frames(1, cut_frames=333, zone_frames=333, declared=365)


def test_contact_positions_stay_inside_the_video():
    duration = 10.0
    positions = build.contact_positions(duration, 7)
    assert len(positions) == 7
    assert positions[0] >= 0
    # Half a frame of headroom: seeking to the exact duration returns no frame.
    assert positions[-1] <= duration - 0.5 / config.FPS
    assert positions == sorted(positions)


def test_contact_positions_handle_a_very_short_clip():
    positions = build.contact_positions(0.2, 7)
    assert all(0 <= p <= 0.2 for p in positions)


def test_contact_positions_reject_an_empty_video():
    with pytest.raises(config.MediaError, match="duration of zero"):
        build.contact_positions(0.0, 7)


@needs_ffmpeg
def test_contact_sheet_covers_the_last_frame_and_cleans_up(tmp_path: Path):
    video = synth_video(tmp_path / "clip.mp4", frames=45)
    sheet = build.contact_sheet(video, tmp_path / "contact.jpg")
    assert sheet.exists() and sheet.stat().st_size > 0
    assert not list(tmp_path.glob(".*-frames"))


@needs_ffmpeg
def test_frame_rate_probe_accepts_thirty(tmp_path: Path):
    video = synth_video(tmp_path / "thirty.mp4", frames=60, fps=30)
    rate = config.require_supported_frame_rate(video)
    assert rate["nominal"] == 30.0
    assert rate["variable"] is False


@needs_ffmpeg
def test_frame_rate_probe_rejects_sixty(tmp_path: Path):
    video = synth_video(tmp_path / "sixty.mp4", frames=60, fps=60)
    assert config.frame_rate(video)["nominal"] == 60.0
    with pytest.raises(config.MediaError) as info:
        config.require_supported_frame_rate(video)
    message = str(info.value)
    assert "60 fps" in message
    # The error has to carry the way out, not just the complaint.
    assert "-vsync cfr" in message and "-r 30" in message


@needs_ffmpeg
def test_cut_refuses_a_sixty_fps_take(tmp_path: Path):
    import sys

    from conftest import SCRIPTS

    video = synth_video(tmp_path / "sixty.mp4", frames=60, fps=60)
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "cut.py"), str(video), "--version", "v1=0-30"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "this skill works in 30 fps frames" in result.stderr
    assert not (tmp_path / "cuts").exists()
