"""sfx.py and setup.py: the two scripts that touch the environment."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from conftest import SCRIPTS, needs_ffmpeg  # noqa: E402

import config  # noqa: E402
import setup as setup_script  # noqa: E402
import sfx  # noqa: E402


@needs_ffmpeg
def test_generates_all_six_sounds(tmp_path: Path):
    assert sfx.is_complete(tmp_path) is False
    written = sfx.generate(tmp_path)
    assert len(written) == len(sfx.SOUNDS)
    assert sfx.is_complete(tmp_path) is True
    for name in sfx.SOUNDS:
        path = tmp_path / "sfx" / f"{name}.wav"
        assert path.stat().st_size > 0


@needs_ffmpeg
def test_existing_sounds_are_kept(tmp_path: Path):
    sfx.generate(tmp_path)
    assert sfx.generate(tmp_path) == []


def test_status_is_json_serializable():
    payload = setup_script.status()
    assert payload["status"] in {"ready", "needs_install", "needs_key", "needs_install_and_key"}
    assert isinstance(payload["missing_binaries"], list)
    json.dumps(payload)


def test_status_never_exposes_the_key():
    payload = json.dumps(setup_script.status())
    key, _ = config.api_key()
    if key:
        assert key not in payload


def test_json_mode_runs():
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "setup.py"), "--json"], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "can_proceed" in json.loads(result.stdout)


def test_env_parsing_strips_inline_comments():
    values = config._parse_env(
        "\n".join(
            [
                "# a comment",
                "PLAIN=value",
                "QUOTED='keep me'",
                "COMMENTED=value  # trailing note",
                "HASHY=abc#123",
                "broken line",
            ]
        )
    )
    assert values == {
        "PLAIN": "value",
        "QUOTED": "keep me",
        "COMMENTED": "value",
        "HASHY": "abc#123",
    }


def test_first_int_survives_ffprobes_trailing_comma():
    # ffprobe's csv writer appends an empty field on some inputs, so a frame
    # count arrives as "300,". Anything stricter reads that as no answer.
    assert config.first_int("300,\n") == 300
    assert config.first_int("42") == 42
    assert config.first_int("\n") is None
    assert config.first_int("N/A") is None
