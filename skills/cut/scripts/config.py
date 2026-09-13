#!/usr/bin/env python3
"""Shared configuration for the /cut skill.

Reads `~/.config/cut/.env` first and falls back to `~/.config/watch/.env`, so
anyone who already uses the `watch` skill (github.com/epictaste/claude-eyes)
has zero configuration to do: both skills need the same Deepgram key.

Pure stdlib. No secrets are ever written to stdout or to output files.
"""
from __future__ import annotations

import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "cut"
CONFIG_FILE = CONFIG_DIR / ".env"

# Fallback config of the sibling `watch` skill — same key, same owner.
FALLBACK_CONFIG_FILE = Path.home() / ".config" / "watch" / ".env"

#: Every frame number in this skill is at this rate. Vertical social video is 30 fps.
FPS = 30

#: Deepgram model and language used for word-level timestamps.
DEFAULT_MODEL = "nova-3"
#: `multi` covers English, German, and clips that mix the two.
DEFAULT_LANGUAGE = "multi"

#: Gap between the top edge of a burned-in subtitle box and the animation zone.
DEFAULT_SUBTITLE_MARGIN = 23

#: Used when no subtitle box is found: the top half of a 1080x1920 frame.
DEFAULT_ZONE_FRACTION = 0.5

#: Sound effects are mixed roughly 10 dB below the spoken voice.
DEFAULT_SFX_VOLUME = 0.32


def _parse_env(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, _, value = raw.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] in ('"', "'") and value[-1] == value[0]:
            value = value[1:-1]
        else:
            # Strip a trailing inline comment from an unquoted value, but keep
            # a '#' that is part of the value itself (hex colors, API keys).
            for i, ch in enumerate(value):
                if ch == "#" and i > 0 and value[i - 1] in " \t":
                    value = value[:i].rstrip()
                    break
        values[key.strip()] = value
    return values


def read_env_file(path: Path) -> dict[str, str]:
    """Parse a dotenv file. Missing or unreadable files yield an empty dict."""
    if not path.exists():
        return {}
    try:
        return _parse_env(path.read_text(encoding="utf-8"))
    except OSError:
        return {}


def config_files() -> list[Path]:
    """Config files in lookup order: own config first, watch's config second."""
    return [CONFIG_FILE, FALLBACK_CONFIG_FILE]


def setting(name: str, default: str | None = None) -> str | None:
    """Read a setting from the environment, then from the config files."""
    env = os.environ.get(name)
    if env and env.strip():
        return env.strip()
    for path in config_files():
        value = read_env_file(path).get(name)
        if value:
            return value
    return default


def api_key() -> tuple[str | None, Path | None]:
    """Return (Deepgram API key, file it came from). (None, None) if unset.

    An environment variable wins over both config files and reports no source
    file, because nothing was read from disk.
    """
    env = os.environ.get("DEEPGRAM_API_KEY")
    if env and env.strip():
        return env.strip(), None
    for path in config_files():
        value = read_env_file(path).get("DEEPGRAM_API_KEY")
        if value:
            return value, path
    return None, None


def model() -> str:
    return setting("CUT_DEEPGRAM_MODEL", DEFAULT_MODEL) or DEFAULT_MODEL


def language() -> str:
    return setting("CUT_DEEPGRAM_LANGUAGE", DEFAULT_LANGUAGE) or DEFAULT_LANGUAGE


# --------------------------------------------------------------------------
# Shared media helpers. Every script in this skill shells out to ffmpeg and
# ffprobe, so the wrappers live here instead of being copied four times.
# --------------------------------------------------------------------------

import json as _json  # noqa: E402
import re as _re  # noqa: E402
import subprocess  # noqa: E402


class MediaError(RuntimeError):
    """A local ffmpeg/ffprobe call failed. Message is meant for the user."""


def run(cmd: list[str], what: str, timeout: int | None = None) -> str:
    """Run a command, return stdout, raise MediaError with stderr on failure."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise MediaError(f"{what}: {cmd[0]} is not installed") from exc
    except subprocess.TimeoutExpired as exc:
        raise MediaError(f"{what}: {cmd[0]} timed out after {timeout}s") from exc
    if result.returncode != 0:
        detail = (result.stderr or "").strip().splitlines()
        tail = detail[-1] if detail else f"exit code {result.returncode}"
        raise MediaError(f"{what} failed: {tail}")
    return result.stdout


def run_binary(cmd: list[str], what: str, timeout: int | None = None) -> bytes:
    """Same as `run`, but returns raw stdout bytes (for piped video frames)."""
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise MediaError(f"{what}: {cmd[0]} is not installed") from exc
    except subprocess.TimeoutExpired as exc:
        raise MediaError(f"{what}: {cmd[0]} timed out after {timeout}s") from exc
    if result.returncode != 0:
        detail = (result.stderr or b"").decode("utf-8", "replace").strip().splitlines()
        tail = detail[-1] if detail else f"exit code {result.returncode}"
        raise MediaError(f"{what} failed: {tail}")
    return result.stdout


def first_int(text: str) -> int | None:
    """First whole number in an ffprobe answer.

    ffprobe's csv writer appends an empty field for some inputs, so a frame
    count can come back as "300,". Parsing the first number instead of the whole
    string keeps that from being read as "no answer".
    """
    match = _re.search(r"\d+", text)
    return int(match.group(0)) if match else None


def probe_stream(video: Path, entries: str) -> list[str]:
    """Read `entries` (an ffprobe -show_entries selector) from the video stream."""
    out = run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", entries,
            "-of", "csv=p=0",
            str(Path(video).resolve()),
        ],
        f"reading {entries} from {Path(video).name}",
    )
    return [p for p in out.strip().replace("\n", ",").split(",") if p]


def frame_count(video: Path) -> int:
    """Exact number of video frames. Decodes the stream, so it is slow but true."""
    out = run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-count_frames",
            "-show_entries", "stream=nb_read_frames",
            "-of", "csv=p=0",
            str(Path(video).resolve()),
        ],
        f"counting frames of {Path(video).name}",
    )
    value = first_int(out)
    if value is None:
        raise MediaError(f"ffprobe returned no frame count for {video}")
    return value


def dimensions(video: Path) -> tuple[int, int]:
    parts = probe_stream(video, "stream=width,height")
    if len(parts) < 2 or not parts[0].isdigit() or not parts[1].isdigit():
        raise MediaError(f"ffprobe returned no dimensions for {video}")
    return int(parts[0]), int(parts[1])


def duration_seconds(video: Path) -> float:
    out = run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            str(Path(video).resolve()),
        ],
        f"reading duration of {Path(video).name}",
    )
    try:
        return float(out.strip())
    except ValueError as exc:
        raise MediaError(f"ffprobe returned no duration for {video}") from exc


def has_audio(video: Path) -> bool:
    out = run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=index",
            "-of", "csv=p=0",
            str(Path(video).resolve()),
        ],
        f"checking audio of {Path(video).name}",
    )
    return bool(out.strip())


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
