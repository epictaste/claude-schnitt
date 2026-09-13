#!/usr/bin/env python3
"""Frame exact cut versions of one take.

A talking-head take often contains several hooks recorded back to back. Each cut
version keeps one hook and the shared body, so one shoot turns into several
versions to test against each other.

Segments are given in frames, half open, at 30 fps. `0-103,370-` means "frames 0
to 102, then frame 370 to the end". After cutting, the frame count of the result
is verified with ffprobe. It has to match exactly, otherwise every word timing in
the animation zone is off.

Usage:
  cut.py take.mp4 --version "v1=0-103,370-" --version "v2=103-238,587-"
  cut.py take.mp4 --version "v1=0-300" --out-dir cuts
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import config  # noqa: E402


def parse_segments(spec: str, total_frames: int) -> list[tuple[int, int]]:
    """Parse `0-103,370-` into [(0, 103), (370, total_frames)]."""
    segments: list[tuple[int, int]] = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
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
        segments.append((start, end))
    if not segments:
        raise ValueError("no segments given")
    return segments


def parse_version(spec: str, total_frames: int) -> tuple[str, list[tuple[int, int]]]:
    """Parse `v1=0-103,370-` into ("v1", [(0, 103), (370, total)])."""
    if "=" not in spec:
        raise ValueError(f"version {spec!r} must look like name=0-103,370-")
    name, _, segment_spec = spec.partition("=")
    name = name.strip()
    if not name or any(ch in name for ch in "/\\ "):
        raise ValueError(f"version name {name!r} must be a plain file name")
    return name, parse_segments(segment_spec, total_frames)


def expected_frames(segments: list[tuple[int, int]]) -> int:
    return sum(end - start for start, end in segments)


def build_filter(segments: list[tuple[int, int]], fps: int, with_audio: bool) -> str:
    """The trim/concat filter graph for one version."""
    parts: list[str] = []
    labels: list[str] = []
    for index, (start, end) in enumerate(segments):
        parts.append(
            f"[0:v]trim=start_frame={start}:end_frame={end},setpts=PTS-STARTPTS[v{index}]"
        )
        labels.append(f"[v{index}]")
        if with_audio:
            parts.append(
                f"[0:a]atrim=start={start / fps:.6f}:end={end / fps:.6f},"
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
    segments: list[tuple[int, int]],
    out_path: Path,
    fps: int,
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
        help="a version, e.g. v1=0-103,370- (repeatable)",
    )
    parser.add_argument(
        "--out-dir", type=Path,
        help="where the cuts land (default: <video-dir>/cuts)",
    )
    parser.add_argument("--fps", type=int, default=config.FPS)
    parser.add_argument("--crf", type=int, default=17, help="x264 quality (default: 17)")
    args = parser.parse_args()

    if not args.video.exists():
        print(f"[cut] no such video: {args.video}", file=sys.stderr)
        return 2

    try:
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

    print(f"[cut] take {args.video.name}: {total_frames} frames at {args.fps} fps", file=sys.stderr)
    for name, segments in versions:
        out_path = out_dir / f"{name}.mp4"
        want = expected_frames(segments)
        try:
            got = cut_version(args.video, segments, out_path, args.fps, args.crf)
        except config.MediaError as exc:
            print(f"[cut] {name}: {exc}", file=sys.stderr)
            failures += 1
            continue

        spans = " + ".join(f"{start}-{end}" for start, end in segments)
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

    print()
    print("Paste into src/timing.ts:")
    print()
    print("export const VERSIONS = {")
    for index, (name, segments) in enumerate(versions, start=1):
        print(f"\t{index}: {{durationInFrames: {expected_frames(segments)}, cut: '{name}.mp4'}},")
    print("} as const;")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
