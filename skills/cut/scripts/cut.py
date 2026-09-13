#!/usr/bin/env python3
"""Frame exact cut versions of one take.

A talking-head take often contains several hooks recorded back to back. Each cut
version keeps one hook and the shared body, so one shoot turns into several
versions to compare against each other. Hooks of different lengths are the normal
case, so every version gets its own layout.

Segments are frames of the take, half open, at 30 fps. Name them after the parts
in `words.json` and this script can print the whole `VERSIONS` block:

  --version "v1=hookA:0-103,body:370-600"
  --version "v2=hookB:103-238,body:370-600"

`hookA:0-103` means frames 0 to 102 of the take, which becomes the part `hookA`.
The same part can appear in several versions; the running start inside each cut
is computed per version.

After cutting, the frame count of every result is verified with ffprobe. It has
to match exactly, otherwise every word timing in the animation zone is off.

Usage:
  cut.py take.mp4 --version "v1=hookA:0-103,body:370-600" --version "v2=hookB:103-238,body:370-600"
  cut.py take.mp4 --version "v1=0-300" --out-dir cuts
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import NamedTuple

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import config  # noqa: E402


class Segment(NamedTuple):
    """A slice of the take. `name` is the part it becomes, if it was named."""

    name: str | None
    start: int
    end: int

    @property
    def frames(self) -> int:
        return self.end - self.start


def parse_segments(spec: str, total_frames: int) -> list[Segment]:
    """Parse `hookA:0-103,body:370-` into segments.

    The part name is optional, so `0-103,370-` still works. Naming is what lets
    this script print the `VERSIONS` layout, so it is what the skill documents.
    """
    segments: list[Segment] = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        name: str | None = None
        if ":" in chunk:
            raw_name, _, chunk = chunk.partition(":")
            name = raw_name.strip()
            if not name.isidentifier():
                raise ValueError(f"part name {name!r} must be a plain identifier (letters, digits, _)")
        if "-" not in chunk:
            raise ValueError(f"segment {chunk!r} needs a range like 0-103")
        raw_start, _, raw_end = chunk.partition("-")
        try:
            start = int(raw_start)
            end = int(raw_end) if raw_end.strip() else total_frames
        except ValueError as exc:
            raise ValueError(f"segment {chunk!r} is not numeric") from exc
        if start < 0:
            raise ValueError(f"segment {chunk!r} starts before frame 0")
        if end <= start:
            raise ValueError(f"segment {chunk!r} is empty or runs backwards")
        if end > total_frames:
            raise ValueError(
                f"segment {chunk!r} ends at frame {end}, but the take has {total_frames} frames"
            )
        segments.append(Segment(name, start, end))
    if not segments:
        raise ValueError("no segments given")
    return segments


def parse_version(spec: str, total_frames: int) -> tuple[str, list[Segment]]:
    """Parse `v1=hookA:0-103,body:370-` into ("v1", [segments])."""
    if "=" not in spec:
        raise ValueError(f"version {spec!r} must look like name=hookA:0-103,body:370-")
    name, _, segment_spec = spec.partition("=")
    name = name.strip()
    if not name or any(ch in name for ch in "/\\ "):
        raise ValueError(f"version name {name!r} must be a plain file name")
    return name, parse_segments(segment_spec, total_frames)


def expected_frames(segments: list[Segment]) -> int:
    return sum(segment.frames for segment in segments)


def placed_parts(segments: list[Segment]) -> list[tuple[str, int, int]]:
    """Parts of one version as (name, start inside the cut, frames).

    The start is the running sum of the segments before it, which is what
    `timing.ts` needs. It is unrelated to where the segment sat in the take.
    """
    placed: list[tuple[str, int, int]] = []
    running = 0
    for index, segment in enumerate(segments, start=1):
        placed.append((segment.name or f"part{index}", running, segment.frames))
        running += segment.frames
    return placed


def versions_snippet(versions: list[tuple[str, list[Segment]]]) -> str:
    """The `VERSIONS` block for src/timing.ts, the one source for the layout."""
    lines = ["export const VERSIONS: Record<number, Version> = {"]
    for number, (name, segments) in enumerate(versions, start=1):
        entries = ", ".join(
            f"{{part: '{part}', frames: {frames}}}" for part, _, frames in placed_parts(segments)
        )
        lines.append(f"\t{number}: {{cut: '{name}.mp4', layout: [{entries}]}},")
    lines.append("};")
    return "\n".join(lines)


def build_filter(segments: list[Segment], fps: int, with_audio: bool) -> str:
    """The trim/concat filter graph for one version."""
    parts: list[str] = []
    labels: list[str] = []
    for index, segment in enumerate(segments):
        parts.append(
            f"[0:v]trim=start_frame={segment.start}:end_frame={segment.end},"
            f"setpts=PTS-STARTPTS[v{index}]"
        )
        labels.append(f"[v{index}]")
        if with_audio:
            parts.append(
                f"[0:a]atrim=start={segment.start / fps:.6f}:end={segment.end / fps:.6f},"
                f"asetpts=PTS-STARTPTS[a{index}]"
            )
            labels.append(f"[a{index}]")
    joined = "".join(labels)
    audio_flag = 1 if with_audio else 0
    outputs = "[v][a]" if with_audio else "[v]"
    parts.append(f"{joined}concat=n={len(segments)}:v=1:a={audio_flag}{outputs}")
    return ";".join(parts)


def cut_version(
    video: Path,
    segments: list[Segment],
    out_path: Path,
    fps: int = config.FPS,
    crf: int = 17,
) -> int:
    """Cut one version and return its verified frame count."""
    with_audio = config.has_audio(video)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-v", "error", "-nostdin", "-y",
        "-i", str(Path(video).resolve()),
        "-filter_complex", build_filter(segments, fps, with_audio),
        "-map", "[v]",
    ]
    if with_audio:
        cmd += ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
    cmd += [
        "-c:v", "libx264", "-crf", str(crf), "-preset", "medium",
        "-pix_fmt", "yuv420p", "-r", str(fps),
        str(out_path.resolve()),
    ]
    config.run(cmd, f"cutting {out_path.name}", timeout=3600)
    return config.frame_count(out_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Cut frame exact versions of a take.")
    parser.add_argument("video", type=Path)
    parser.add_argument(
        "--version", action="append", required=True, metavar="NAME=SEGMENTS",
        help="a version, e.g. v1=hookA:0-103,body:370- (repeatable)",
    )
    parser.add_argument(
        "--out-dir", type=Path,
        help="where the cuts land (default: <video-dir>/cuts)",
    )
    parser.add_argument("--crf", type=int, default=17, help="x264 quality (default: 17)")
    args = parser.parse_args()

    if not args.video.exists():
        print(f"[cut] no such video: {args.video}", file=sys.stderr)
        return 2

    try:
        rate = config.require_supported_frame_rate(args.video)
        total_frames = config.frame_count(args.video)
    except config.MediaError as exc:
        print(f"[cut] {exc}", file=sys.stderr)
        return 1

    try:
        versions = [parse_version(spec, total_frames) for spec in args.version]
    except ValueError as exc:
        print(f"[cut] {exc}", file=sys.stderr)
        return 2

    out_dir = args.out_dir or args.video.parent / "cuts"
    failures = 0

    print(
        f"[cut] take {args.video.name}: {total_frames} frames at {rate['nominal']:g} fps",
        file=sys.stderr,
    )
    for name, segments in versions:
        out_path = out_dir / f"{name}.mp4"
        want = expected_frames(segments)
        try:
            got = cut_version(args.video, segments, out_path, config.FPS, args.crf)
        except config.MediaError as exc:
            print(f"[cut] {name}: {exc}", file=sys.stderr)
            failures += 1
            continue

        spans = " + ".join(f"{segment.start}-{segment.end}" for segment in segments)
        if got == want:
            print(f"{name}: {got} frames ({spans}) -> {out_path}")
        else:
            print(
                f"[cut] {name}: expected {want} frames, ffprobe counted {got} in {out_path}. "
                "Do not build on this cut, the word timings would drift.",
                file=sys.stderr,
            )
            failures += 1

    if failures:
        return 1

    unnamed = [name for name, segments in versions if any(s.name is None for s in segments)]
    print()
    print("Paste into src/timing.ts:")
    print()
    print(versions_snippet(versions))
    if unnamed:
        print()
        print(
            "[cut] note: " + ", ".join(unnamed) + " had unnamed segments, so the layout above "
            "uses placeholder part names. Re-run with names that match words.json, "
            "e.g. --version \"v1=hookA:0-103,body:370-\".",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
