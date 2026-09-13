#!/usr/bin/env python3
"""Measure how tall the animation zone above the speaker can be.

The zone is the top slice of the frame that gets replaced by graphics. Its
height is decided by whatever must stay visible underneath: with burned-in
subtitles, the zone has to end above the subtitle box.

So this scans a few frames for the top edge of a dark subtitle box and subtracts
a small margin. If no box is found, it falls back to half the frame height.

No image library: ffmpeg writes a raw grayscale frame to stdout and the scan is
plain Python over those bytes.

Usage:
  zone.py take.mp4
  zone.py take.mp4 --json
  zone.py take.mp4 --samples 8 --threshold 60 --margin 23
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import config  # noqa: E402

#: A subtitle box is darker than this on a 0-255 grayscale scale.
DEFAULT_THRESHOLD = 60

#: How many rows must stay dark before a row counts as the top of a box. Stops a
#: single dark line (hair, a shadow, a hard edge) from being read as the box.
DEFAULT_RUN = 10

#: Rows outside this band are never considered. Subtitles sit in the middle of a
#: vertical video, never in the top fifth or the bottom fifth.
SCAN_TOP = 0.30
SCAN_BOTTOM = 0.85

#: Columns sampled across the middle of the frame, where subtitle text lives.
SCAN_LEFT = 0.28
SCAN_RIGHT = 0.72


def row_means(
    frame: bytes,
    width: int,
    height: int,
    left: float = SCAN_LEFT,
    right: float = SCAN_RIGHT,
) -> list[float]:
    """Average brightness per row, sampled across the middle columns."""
    if len(frame) < width * height:
        raise ValueError(
            f"frame is {len(frame)} bytes, expected at least {width * height} "
            f"for {width}x{height} grayscale"
        )
    x_from = int(width * left)
    x_to = int(width * right)
    step = max(1, width // 108)
    columns = list(range(x_from, x_to, step)) or [width // 2]
    means: list[float] = []
    for y in range(height):
        base = y * width
        total = 0
        for x in columns:
            total += frame[base + x]
        means.append(total / len(columns))
    return means


def find_box_top(
    frame: bytes,
    width: int,
    height: int,
    threshold: int = DEFAULT_THRESHOLD,
    run: int = DEFAULT_RUN,
) -> int | None:
    """First row of a sustained dark band, or None if there is no box."""
    means = row_means(frame, width, height)
    first = int(height * SCAN_TOP)
    last = int(height * SCAN_BOTTOM)
    for y in range(first, last):
        if means[y] >= threshold:
            continue
        band = means[y : y + run]
        if len(band) == run and all(value < threshold for value in band):
            return y
    return None


def consensus(tops: list[int], spread: int = 200) -> int | None:
    """Agree on one box top across several sampled frames.

    Takes the highest edge among the samples that cluster around the median, so
    a two-line subtitle keeps the zone clear while a single odd frame (a dark
    shirt, a cut to black) cannot drag the zone up.
    """
    if not tops:
        return None
    ordered = sorted(tops)
    median = ordered[len(ordered) // 2]
    clustered = [t for t in ordered if abs(t - median) <= spread]
    return min(clustered) if clustered else median


def grab_gray_frame(video: Path, at_seconds: float, width: int, height: int) -> bytes:
    """One frame at `at_seconds` as raw 8-bit grayscale bytes."""
    return config.run_binary(
        [
            "ffmpeg", "-v", "error", "-nostdin",
            "-ss", f"{at_seconds:.3f}",
            "-i", str(Path(video).resolve()),
            "-frames:v", "1",
            "-f", "rawvideo", "-pix_fmt", "gray", "-",
        ],
        f"grabbing a frame at {at_seconds:.1f}s from {video.name}",
        timeout=120,
    )


def measure(
    video: Path,
    samples: int = 5,
    threshold: int = DEFAULT_THRESHOLD,
    margin: int = config.DEFAULT_SUBTITLE_MARGIN,
) -> dict:
    width, height = config.dimensions(video)
    duration = config.duration_seconds(video)

    # Spread the samples across the middle of the clip: the first and last
    # second often have no speech and therefore no subtitles.
    span_start = duration * 0.1
    span_end = duration * 0.9
    if samples < 1:
        samples = 1
    step = (span_end - span_start) / samples if samples > 1 else 0.0
    timestamps = [span_start + step * i for i in range(samples)]

    found: list[dict] = []
    for at in timestamps:
        try:
            frame = grab_gray_frame(video, at, width, height)
        except config.MediaError:
            continue
        if len(frame) < width * height:
            continue
        top = find_box_top(frame, width, height, threshold)
        found.append({"at": round(at, 2), "boxTop": top})

    tops = [entry["boxTop"] for entry in found if entry["boxTop"] is not None]
    box_top = consensus(tops)

    if box_top is None:
        zone_height = int(height * config.DEFAULT_ZONE_FRACTION)
        method = "fallback-half-frame"
    else:
        zone_height = box_top - margin
        method = "subtitle-box"

    zone_height = max(1, min(zone_height, height))
    # Even heights only: h264 needs an even pixel height.
    zone_height -= zone_height % 2

    return {
        "video": str(video),
        "width": width,
        "height": height,
        "durationSeconds": round(duration, 2),
        "samples": found,
        "boxTop": box_top,
        "margin": margin,
        "zoneHeight": zone_height,
        "method": method,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure the animation zone height above burned-in subtitles."
    )
    parser.add_argument("video", type=Path)
    parser.add_argument("--samples", type=int, default=5, help="frames to scan (default: 5)")
    parser.add_argument(
        "--threshold", type=int, default=DEFAULT_THRESHOLD,
        help=f"a row this dark counts as subtitle box (default: {DEFAULT_THRESHOLD})",
    )
    parser.add_argument(
        "--margin", type=int, default=config.DEFAULT_SUBTITLE_MARGIN,
        help=f"gap between zone and box (default: {config.DEFAULT_SUBTITLE_MARGIN})",
    )
    parser.add_argument("--json", action="store_true", help="print the full measurement as JSON")
    args = parser.parse_args()

    if not args.video.exists():
        print(f"[cut] no such video: {args.video}", file=sys.stderr)
        return 2

    try:
        result = measure(args.video, args.samples, args.threshold, args.margin)
    except config.MediaError as exc:
        print(f"[cut] {exc}", file=sys.stderr)
        return 1

    if args.json:
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    print(f"{result['width']}x{result['height']}, {result['durationSeconds']}s")
    if result["method"] == "subtitle-box":
        print(f"subtitle box starts at y={result['boxTop']} (margin {result['margin']})")
    else:
        print("no subtitle box found, falling back to half the frame height")
    print(f"ZONE = {{width: {result['width']}, height: {result['zoneHeight']}}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
