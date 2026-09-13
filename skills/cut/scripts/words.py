#!/usr/bin/env python3
"""Word-level timestamps for a video, grouped into parts, as frame numbers.

The video is the truth: every scene change in the animation zone sits on a word
that was actually spoken. To make that possible, this script extracts the audio,
sends it to Deepgram, and writes `words.json`:

    {
      "hook":    {"durationFrames": 130, "words": [{"word": "Start", "frame": 0, "frameEnd": 12}, ...]},
      "example": {"durationFrames": 309, "words": [...]}
    }

Frames are relative to the start of each part, at 30 fps, so a part file can use
frame 0 as its own beginning.

Part ranges are frames of the take. They are usually not known before the
structure of the video is settled, so the normal flow is: transcribe once while
keeping the raw response, then re-split from that file as often as needed
without uploading anything again.

Usage:
  words.py take.mp4 --raw-out raw.json
  words.py take.mp4 --from-json raw.json --parts hookA:0-103,hookB:103-238,body:370-600
  words.py take.mp4 --parts hook:0-130,demo:130-439,cta:439-

Pure stdlib. Only the extracted audio leaves the machine, never the video.
"""
from __future__ import annotations

import argparse
import json
import ssl
import sys
import time
import urllib.error
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import config  # noqa: E402

DEEPGRAM_ENDPOINT = "https://api.deepgram.com/v1/listen"
MAX_ATTEMPTS = 4
RETRY_BASE_DELAY = 2.0


# ---------------------------------------------------------------------------
# Parsing (no network, no ffmpeg — this is what the tests cover)
# ---------------------------------------------------------------------------


def parse_parts(spec: str, total_frames: int) -> list[tuple[str, int, int]]:
    """Parse `name:start-end,name:start-` into [(name, start, end)] in frames.

    An empty end means "until the end of the video". Ranges are half open, so
    `hook:0-130` is frames 0 to 129 and the next part starts at 130.
    """
    parts: list[tuple[str, int, int]] = []
    seen: set[str] = set()
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" not in chunk:
            raise ValueError(f"part {chunk!r} is missing a range, expected name:start-end")
        name, _, span = chunk.partition(":")
        name = name.strip()
        if not name.isidentifier():
            raise ValueError(f"part name {name!r} must be a plain identifier (letters, digits, _)")
        if name in seen:
            raise ValueError(f"part name {name!r} is used twice")
        seen.add(name)
        if "-" not in span:
            raise ValueError(f"part {name!r} needs a range like 0-130, got {span!r}")
        raw_start, _, raw_end = span.partition("-")
        try:
            start = int(raw_start)
            end = int(raw_end) if raw_end.strip() else total_frames
        except ValueError as exc:
            raise ValueError(f"part {name!r} has a non-numeric range: {span!r}") from exc
        if start < 0 or end <= start:
            raise ValueError(f"part {name!r} has an empty or negative range: {start}-{end}")
        if end > total_frames:
            raise ValueError(
                f"part {name!r} ends at frame {end}, but the video has {total_frames} frames"
            )
        parts.append((name, start, end))

    if not parts:
        raise ValueError("no parts parsed from --parts")

    ordered = sorted(parts, key=lambda p: p[1])
    for (a_name, _, a_end), (b_name, b_start, _) in zip(ordered, ordered[1:]):
        if b_start < a_end:
            raise ValueError(f"parts {a_name!r} and {b_name!r} overlap")
    return parts


def words_from_response(payload: dict) -> list[dict]:
    """Flatten a Deepgram response into [{word, start, end}] in seconds.

    Prefers the punctuated form, because that is what a viewer hears as a
    sentence, and keeps the order Deepgram returned.
    """
    results = payload.get("results") or {}
    out: list[dict] = []

    for channel in results.get("channels") or []:
        for alternative in channel.get("alternatives") or []:
            for word in alternative.get("words") or []:
                text = (word.get("punctuated_word") or word.get("word") or "").strip()
                if not text:
                    continue
                out.append(
                    {
                        "word": text,
                        "start": float(word.get("start") or 0.0),
                        "end": float(word.get("end") or 0.0),
                    }
                )
            if out:
                break
        if out:
            break

    if out:
        return out

    # Fallback: some responses carry words only inside the utterances.
    for utterance in results.get("utterances") or []:
        for word in utterance.get("words") or []:
            text = (word.get("punctuated_word") or word.get("word") or "").strip()
            if not text:
                continue
            out.append(
                {
                    "word": text,
                    "start": float(word.get("start") or 0.0),
                    "end": float(word.get("end") or 0.0),
                }
            )
    return out


def split_into_parts(
    words: list[dict],
    parts: list[tuple[str, int, int]],
    fps: int = config.FPS,
) -> dict:
    """Map absolute word times onto per-part frame numbers.

    A word belongs to the part its start frame falls into. `frameEnd` is clamped
    to the part length, so a word that runs over a cut does not point past the
    end of its part.
    """
    result: dict = {}
    for name, start, end in parts:
        duration = end - start
        bucket = []
        for word in words:
            frame = round(word["start"] * fps)
            if frame < start or frame >= end:
                continue
            frame_end = round(word["end"] * fps)
            bucket.append(
                {
                    "word": word["word"],
                    "frame": max(0, frame - start),
                    "frameEnd": max(0, min(frame_end - start, duration)),
                }
            )
        result[name] = {"durationFrames": duration, "words": bucket}
    return result


def parts_summary(grouped: dict) -> str:
    """What was written, in the order the parts start.

    Deliberately not a `VERSIONS` block: the layout of a version comes from
    cut.py, which is the only script that knows which parts end up in which cut
    and in what order. Two scripts printing two versions of the same truth is
    how a project ends up a few frames out.
    """
    lines = ["Parts in words.json:"]
    for name, data in grouped.items():
        lines.append(f"  {name}: {data['durationFrames']} frames, {len(data['words'])} words")
    lines.append("")
    lines.append("VERSIONS for src/timing.ts comes from cut.py, not from here.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Audio + Deepgram
# ---------------------------------------------------------------------------


def extract_audio(video: Path, out_path: Path) -> Path:
    """Mono 16 kHz 64 kbps mp3, roughly 480 kB per minute."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    config.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(Path(video).resolve()),
            "-vn", "-acodec", "libmp3lame", "-ar", "16000", "-ac", "1", "-b:a", "64k",
            str(out_path.resolve()),
        ],
        f"extracting audio from {video.name}",
    )
    if not out_path.exists() or out_path.stat().st_size == 0:
        raise config.MediaError(f"{video.name} produced no audio, it may have no audio track")
    return out_path


def post_to_deepgram(key: str, audio: Path, model: str, language: str) -> dict:
    query = urlencode(
        {
            "model": model,
            "language": language,
            "punctuate": "true",
            "utterances": "true",
        }
    )
    request_body = audio.read_bytes()
    headers = {"Authorization": f"Token {key}", "Content-Type": "audio/mpeg"}
    context = ssl.create_default_context()
    last_error = ""

    for attempt in range(MAX_ATTEMPTS):
        request = Request(
            f"{DEEPGRAM_ENDPOINT}?{query}", data=request_body, headers=headers, method="POST"
        )
        try:
            with urlopen(request, timeout=600, context=context) as response:
                payload = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            detail = _error_body(exc)
            if exc.code in (400, 401, 403):
                raise SystemExit(
                    f"[cut] Deepgram rejected the request (HTTP {exc.code}){detail}\n"
                    f"       A 401 usually means the key in {config.CONFIG_FILE} is wrong."
                )
            last_error = f"HTTP {exc.code}{detail}"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        else:
            try:
                return json.loads(payload)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"[cut] Deepgram returned no JSON: {exc}: {payload[:200]}")

        if attempt < MAX_ATTEMPTS - 1:
            delay = RETRY_BASE_DELAY * (2**attempt)
            print(
                f"[cut] Deepgram {last_error} — retrying in {delay:.0f}s "
                f"(attempt {attempt + 2} of {MAX_ATTEMPTS})",
                file=sys.stderr,
            )
            time.sleep(delay)

    raise SystemExit(f"[cut] Deepgram failed after {MAX_ATTEMPTS} attempts: {last_error}")


def _error_body(exc: urllib.error.HTTPError) -> str:
    try:
        body = exc.read()
    except Exception:
        return ""
    if not body:
        return ""
    return " — " + body.decode("utf-8", errors="replace")[:400]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write word-level frame timings for a video to words.json."
    )
    parser.add_argument("video", type=Path, help="the video to transcribe")
    parser.add_argument(
        "--parts",
        help="part ranges in frames, e.g. hook:0-130,demo:130-439,cta:439- "
        "(default: one part called 'main' covering the whole video)",
    )
    parser.add_argument("--out", type=Path, help="output path (default: <video-dir>/words.json)")
    parser.add_argument("--raw-out", type=Path, help="also keep the raw Deepgram response here")
    parser.add_argument(
        "--from-json",
        type=Path,
        help="reparse a saved Deepgram response instead of calling the API",
    )
    parser.add_argument("--model", help=f"Deepgram model (default: {config.DEFAULT_MODEL})")
    parser.add_argument("--language", help=f"language (default: {config.DEFAULT_LANGUAGE})")
    args = parser.parse_args()

    video = args.video
    if not video.exists():
        print(f"[cut] no such video: {video}", file=sys.stderr)
        return 2

    try:
        config.require_supported_frame_rate(video)
        total_frames = config.frame_count(video)
    except config.MediaError as exc:
        print(f"[cut] {exc}", file=sys.stderr)
        return 1

    try:
        parts = (
            parse_parts(args.parts, total_frames)
            if args.parts
            else [("main", 0, total_frames)]
        )
    except ValueError as exc:
        print(f"[cut] {exc}", file=sys.stderr)
        return 2

    if args.from_json:
        try:
            payload = json.loads(args.from_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[cut] cannot read {args.from_json}: {exc}", file=sys.stderr)
            return 1
    else:
        key, source = config.api_key()
        if not key:
            print(
                "[cut] no Deepgram API key. Set DEEPGRAM_API_KEY in "
                f"{config.CONFIG_FILE} (or {config.FALLBACK_CONFIG_FILE}). "
                f"Run: python3 {SCRIPT_DIR / 'setup.py'}",
                file=sys.stderr,
            )
            return 3
        model = args.model or config.model()
        language = args.language or config.language()
        print(
            f"[cut] transcribing {video.name} with Deepgram {model} (language={language})",
            file=sys.stderr,
        )
        try:
            with TemporaryDirectory(prefix="cut-audio-") as tmp:
                audio = extract_audio(video, Path(tmp) / "audio.mp3")
                size_kb = audio.stat().st_size / 1024
                print(f"[cut] uploading {size_kb:.0f} kB of audio", file=sys.stderr)
                payload = post_to_deepgram(key, audio, model, language)
        except config.MediaError as exc:
            print(f"[cut] {exc}", file=sys.stderr)
            return 1
        if source:
            print(f"[cut] key read from {source}", file=sys.stderr)

    words = words_from_response(payload)
    if not words:
        print("[cut] Deepgram returned no words. Is there speech on the audio track?", file=sys.stderr)
        return 1

    grouped = split_into_parts(words, parts, config.FPS)
    empty = [name for name, data in grouped.items() if not data["words"]]
    if empty:
        print(
            "[cut] warning: no words fall into these parts: " + ", ".join(empty),
            file=sys.stderr,
        )

    out_path = args.out or video.parent / "words.json"
    config.write_json(out_path, grouped)
    if args.raw_out:
        config.write_json(args.raw_out, payload)

    print(f"[cut] {len(words)} words over {total_frames} frames", file=sys.stderr)
    print(f"[cut] wrote {out_path}", file=sys.stderr)
    print()
    print(parts_summary(grouped))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
