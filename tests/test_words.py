"""words.py: Deepgram parsing and the frame math, without touching the network."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import REPO_ROOT, SCRIPTS, needs_ffmpeg, synth_video  # noqa: E402

import words  # noqa: E402

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "deepgram-response.json"


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_words_use_the_punctuated_form():
    parsed = words.words_from_response(load_fixture())
    assert [w["word"] for w in parsed] == [
        "Start", "Here.", "Then", "run", "one", "command,", "and", "you", "are", "done.",
    ]
    assert parsed[0]["start"] == 0.0
    assert parsed[-1]["end"] == 7.2


def test_words_fall_back_to_utterances():
    payload = {"results": {"utterances": load_fixture()["results"]["utterances"]}}
    parsed = words.words_from_response(payload)
    assert [w["word"] for w in parsed] == ["Start", "Here."]


def test_empty_response_yields_no_words():
    assert words.words_from_response({}) == []
    assert words.words_from_response({"results": {"channels": []}}) == []


def test_parse_parts_resolves_open_end():
    parts = words.parse_parts("hook:0-60,body:60-", 270)
    assert parts == [("hook", 0, 60), ("body", 60, 270)]


def test_parse_parts_rejects_bad_input():
    with pytest.raises(ValueError, match="missing a range"):
        words.parse_parts("hook", 100)
    with pytest.raises(ValueError, match="used twice"):
        words.parse_parts("hook:0-10,hook:10-20", 100)
    with pytest.raises(ValueError, match="overlap"):
        words.parse_parts("a:0-50,b:30-80", 100)
    with pytest.raises(ValueError, match="but the video has"):
        words.parse_parts("a:0-500", 100)
    with pytest.raises(ValueError, match="empty or negative"):
        words.parse_parts("a:50-50", 100)
    with pytest.raises(ValueError, match="plain identifier"):
        words.parse_parts("my part:0-10", 100)


def test_frames_are_relative_to_the_part():
    parsed = words.words_from_response(load_fixture())
    parts = words.parse_parts("hook:0-60,body:60-", 270)
    grouped = words.split_into_parts(parsed, parts, fps=30)

    assert grouped["hook"]["durationFrames"] == 60
    assert grouped["body"]["durationFrames"] == 210

    # "Start" at 0.0s is frame 0 of the hook; "Then" at 2.0s is frame 60 absolute,
    # which is frame 0 of the body.
    assert grouped["hook"]["words"][0] == {"word": "Start", "frame": 0, "frameEnd": 12}
    assert grouped["body"]["words"][0] == {"word": "Then", "frame": 0, "frameEnd": 9}
    assert [w["word"] for w in grouped["hook"]["words"]] == ["Start", "Here."]
    assert len(grouped["body"]["words"]) == 8


def test_frame_end_is_clamped_to_the_part():
    parsed = [{"word": "over", "start": 1.9, "end": 4.0}]
    grouped = words.split_into_parts(parsed, [("hook", 0, 60)], fps=30)
    assert grouped["hook"]["words"][0]["frameEnd"] == 60


def test_parts_summary_reports_what_was_written_and_nothing_else():
    grouped = {
        "hook": {"durationFrames": 60, "words": [{"word": "a", "frame": 0, "frameEnd": 3}]},
        "body": {"durationFrames": 210, "words": []},
    }
    summary = words.parts_summary(grouped)
    assert "hook: 60 frames, 1 words" in summary
    assert "body: 210 frames, 0 words" in summary
    # The layout of a version belongs to cut.py. Two scripts printing it is how
    # a project ends up a few frames out.
    assert "VERSIONS" in summary and "comes from cut.py" in summary
    assert "layout:" not in summary


@needs_ffmpeg
def test_cli_reparses_a_saved_response(tmp_path: Path):
    video = synth_video(tmp_path / "take.mp4", frames=270)
    out = tmp_path / "words.json"
    result = subprocess.run(
        [
            sys.executable, str(SCRIPTS / "words.py"), str(video),
            "--parts", "hook:0-60,body:60-",
            "--from-json", str(FIXTURE),
            "--out", str(out),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    written = json.loads(out.read_text(encoding="utf-8"))
    assert set(written) == {"hook", "body"}
    assert written["hook"]["words"][0]["word"] == "Start"
    assert "Parts in words.json:" in result.stdout
    assert "export const VERSIONS" not in result.stdout
