"""cut.py: segment math and a real frame-exact cut."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from conftest import SCRIPTS, needs_ffmpeg, synth_video  # noqa: E402

import config  # noqa: E402
import cut  # noqa: E402


def test_parse_segments_resolves_the_open_end():
    assert cut.parse_segments("0-103,370-", 600) == [
        cut.Segment(None, 0, 103),
        cut.Segment(None, 370, 600),
    ]


def test_parse_segments_keeps_the_part_names():
    segments = cut.parse_segments("hookA:0-103,body:370-", 600)
    assert [s.name for s in segments] == ["hookA", "body"]
    assert [s.frames for s in segments] == [103, 230]


def test_parse_segments_rejects_a_bad_part_name():
    with pytest.raises(ValueError, match="plain identifier"):
        cut.parse_segments("my part:0-10", 600)


def test_parse_segments_rejects_bad_input():
    with pytest.raises(ValueError, match="needs a range"):
        cut.parse_segments("103", 600)
    with pytest.raises(ValueError, match="not numeric"):
        cut.parse_segments("a-b", 600)
    with pytest.raises(ValueError, match="empty or runs backwards"):
        cut.parse_segments("300-300", 600)
    with pytest.raises(ValueError, match="but the take has"):
        cut.parse_segments("0-900", 600)


def test_parse_version_splits_name_and_segments():
    name, segments = cut.parse_version("v2=hookB:103-238,body:587-", 900)
    assert name == "v2"
    assert [(s.name, s.start, s.end) for s in segments] == [
        ("hookB", 103, 238),
        ("body", 587, 900),
    ]


def test_parse_version_rejects_a_path_as_name():
    with pytest.raises(ValueError, match="plain file name"):
        cut.parse_version("../v1=0-10", 900)


def test_expected_frames_sums_the_segments():
    assert cut.expected_frames(cut.parse_segments("0-103,370-600", 600)) == 333


def test_placed_parts_are_a_running_sum_inside_the_cut():
    # Take positions 0-103 and 370-600 become 0 and 103 inside the cut: the
    # layout is relative to the version, never to the take.
    segments = cut.parse_segments("hookA:0-103,body:370-600", 600)
    assert cut.placed_parts(segments) == [("hookA", 0, 103), ("body", 103, 230)]


def test_placed_parts_fall_back_to_generic_names():
    segments = cut.parse_segments("0-40,60-100", 100)
    assert cut.placed_parts(segments) == [("part1", 0, 40), ("part2", 40, 40)]


def test_versions_snippet_gives_each_version_its_own_layout():
    versions = [
        ("v1", cut.parse_segments("hookA:0-103,body:370-600", 600)),
        ("v2", cut.parse_segments("hookB:103-238,body:370-600", 600)),
    ]
    snippet = cut.versions_snippet(versions)
    assert "1: {cut: 'v1.mp4', layout: [{part: 'hookA', frames: 103}, {part: 'body', frames: 230}]}," in snippet
    assert "2: {cut: 'v2.mp4', layout: [{part: 'hookB', frames: 135}, {part: 'body', frames: 230}]}," in snippet
    assert "Record<number, Version>" in snippet


def test_filter_graph_covers_video_and_audio():
    graph = cut.build_filter(cut.parse_segments("0-10,20-30", 30), fps=30, with_audio=True)
    assert "trim=start_frame=0:end_frame=10" in graph
    assert "trim=start_frame=20:end_frame=30" in graph
    assert "atrim=start=0.666667:end=1.000000" in graph
    assert graph.endswith("[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]")


def test_filter_graph_without_audio():
    graph = cut.build_filter(cut.parse_segments("0-10", 30), fps=30, with_audio=False)
    assert "atrim" not in graph
    assert graph.endswith("[v0]concat=n=1:v=1:a=0[v]")


@needs_ffmpeg
def test_cut_produces_the_exact_frame_count(tmp_path: Path):
    take = synth_video(tmp_path / "take.mp4", frames=120)
    out = tmp_path / "v1.mp4"
    segments = cut.parse_segments("hook:0-30,body:60-120", 120)

    counted = cut.cut_version(take, segments, out)

    assert counted == cut.expected_frames(segments) == 90
    assert config.frame_count(out) == 90


@needs_ffmpeg
def test_cli_reports_every_version(tmp_path: Path):
    take = synth_video(tmp_path / "take.mp4", frames=120)
    result = subprocess.run(
        [
            sys.executable, str(SCRIPTS / "cut.py"), str(take),
            "--version", "v1=hookA:0-40",
            "--version", "v2=hookB:40-",
            "--out-dir", str(tmp_path / "cuts"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "v1: 40 frames" in result.stdout
    assert "v2: 80 frames" in result.stdout
    assert "{part: 'hookA', frames: 40}" in result.stdout
    assert "{part: 'hookB', frames: 80}" in result.stdout
    assert config.frame_count(tmp_path / "cuts" / "v1.mp4") == 40
    assert config.frame_count(tmp_path / "cuts" / "v2.mp4") == 80


@needs_ffmpeg
def test_cli_refuses_a_segment_past_the_end(tmp_path: Path):
    take = synth_video(tmp_path / "take.mp4", frames=60)
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "cut.py"), str(take), "--version", "v1=0-600"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "but the take has 60 frames" in result.stderr
