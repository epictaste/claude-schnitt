#!/usr/bin/env python3
"""Render the animation zone, lay it over the cut, and build a contact sheet.

Three things happen here, in this order:

1. Remotion renders the zone composition `Top-V<N>` to an MP4 the size of the
   zone. The render log goes to a file, never to a pipe: a pipe that closes
   early kills the render with SIGPIPE halfway through.
2. ffmpeg overlays that zone onto the matching cut at 0:0 and mixes the sound
   effect track about 10 dB under the voice.
3. Seven frames of the result are stacked into one contact sheet, so the edge,
   the subtitle box, and the sync can be checked at a glance.

Usage:
  build.py cut-my-clip 1
  build.py cut-my-clip 2 --skip-render
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import config  # noqa: E402
import sfx as sfx_module  # noqa: E402

VERSION_PATTERN = re.compile(
    r"(\d+)\s*:\s*\{[^}]*?durationInFrames\s*:\s*(\d+)[^}]*?cut\s*:\s*['\"]([^'\"]+)['\"]"
)

CONTACT_FRAMES = 7


def read_version(project: Path, version: int) -> tuple[int | None, str]:
    """Get (durationInFrames, cut file) for a version out of src/timing.ts.

    Falls back to (None, "cut.mp4") when timing.ts cannot be parsed, so a
    renamed or reformatted file degrades into a warning rather than a crash.
    """
    timing = project / "src" / "timing.ts"
    if not timing.exists():
        return None, "cut.mp4"
    try:
        text = timing.read_text(encoding="utf-8")
    except OSError:
        return None, "cut.mp4"
    block = text.split("VERSIONS", 1)
    if len(block) < 2:
        return None, "cut.mp4"
    for number, duration, cut_file in VERSION_PATTERN.findall(block[1]):
        if int(number) == version:
            return int(duration), cut_file
    return None, "cut.mp4"


def ensure_dependencies(project: Path, log_dir: Path) -> None:
    if (project / "node_modules").is_dir():
        return
    log_file = log_dir / "npm-install.log"
    print(f"[cut] installing node dependencies (log: {log_file})", file=sys.stderr)
    with log_file.open("w", encoding="utf-8") as log:
        result = subprocess.run(
            ["npm", "install", "--no-audit", "--no-fund"],
            cwd=project, stdout=log, stderr=subprocess.STDOUT,
        )
    if result.returncode != 0:
        raise config.MediaError(f"npm install failed, see {log_file}")


def render_zone(project: Path, version: int, out_path: Path, log_dir: Path, crf: int) -> Path:
    """Run Remotion. Output goes to a log file, never to a pipe."""
    log_file = log_dir / f"render-v{version}.log"
    composition = f"Top-V{version}"
    cmd = [
        "npx", "remotion", "render", composition, str(out_path.resolve()),
        "--codec=h264", f"--crf={crf}",
    ]
    print(f"[cut] rendering {composition} (log: {log_file})", file=sys.stderr)
    with log_file.open("w", encoding="utf-8") as log:
        result = subprocess.run(cmd, cwd=project, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode != 0 or not out_path.exists():
        tail = _tail(log_file)
        raise config.MediaError(
            f"remotion render of {composition} failed (exit {result.returncode}).\n{tail}"
        )
    return out_path


def _tail(log_file: Path, lines: int = 15) -> str:
    try:
        content = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return f"       (no log at {log_file})"
    return "\n".join("       " + line for line in content[-lines:])


def overlay(cut: Path, zone: Path, out_path: Path, sfx_volume: float, crf: int) -> Path:
    """Zone over cut, sound effects mixed under the original voice."""
    zone_has_audio = config.has_audio(zone)
    cut_has_audio = config.has_audio(cut)

    if zone_has_audio and cut_has_audio:
        filter_graph = (
            "[0:v][1:v]overlay=0:0:shortest=1[v];"
            f"[1:a]volume={sfx_volume}[sfx];"
            "[0:a][sfx]amix=inputs=2:duration=first:normalize=0[a]"
        )
        maps = ["-map", "[v]", "-map", "[a]"]
    else:
        filter_graph = "[0:v][1:v]overlay=0:0:shortest=1[v]"
        maps = ["-map", "[v]"] + (["-map", "0:a"] if cut_has_audio else [])

    cmd = [
        "ffmpeg", "-v", "error", "-nostdin", "-y",
        "-i", str(cut.resolve()), "-i", str(zone.resolve()),
        "-filter_complex", filter_graph, *maps,
        "-c:v", "libx264", "-crf", str(crf), "-preset", "medium", "-pix_fmt", "yuv420p",
    ]
    if cut_has_audio:
        cmd += ["-c:a", "aac", "-b:a", "192k"]
    cmd += [str(out_path.resolve())]
    config.run(cmd, f"compositing {out_path.name}", timeout=3600)
    return out_path


def contact_sheet(video: Path, out_path: Path, columns: int = CONTACT_FRAMES) -> Path:
    """One wide JPEG out of evenly spaced frames."""
    duration = config.duration_seconds(video)
    stills: list[Path] = []
    tmp_dir = out_path.parent / f".{out_path.stem}-frames"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    for index in range(columns):
        position = duration * (0.03 + 0.94 * index / max(1, columns - 1))
        still = tmp_dir / f"{index:02d}.png"
        config.run(
            [
                "ffmpeg", "-v", "error", "-nostdin", "-y",
                "-ss", f"{position:.3f}", "-i", str(video.resolve()),
                "-frames:v", "1", "-vf", "scale=320:-2", str(still),
            ],
            f"grabbing contact frame {index + 1}",
        )
        stills.append(still)

    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-y"]
    for still in stills:
        cmd += ["-i", str(still)]
    cmd += ["-filter_complex", f"hstack=inputs={len(stills)}", "-q:v", "3", str(out_path.resolve())]
    config.run(cmd, "stacking the contact sheet")

    for still in stills:
        still.unlink(missing_ok=True)
    tmp_dir.rmdir()
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the zone and composite one version.")
    parser.add_argument("project", type=Path, help="the cut-<slug> project directory")
    parser.add_argument("version", type=int, help="version number, matching Top-V<N>")
    parser.add_argument("--cut", type=Path, help="override the cut video (default: from timing.ts)")
    parser.add_argument("--skip-render", action="store_true", help="reuse the zone MP4 from a previous run")
    parser.add_argument("--sfx-volume", type=float, default=config.DEFAULT_SFX_VOLUME)
    parser.add_argument("--crf", type=int, default=17, help="x264 quality of the final file")
    parser.add_argument("--render-crf", type=int, default=16, help="x264 quality of the zone render")
    parser.add_argument("--no-contact-sheet", action="store_true")
    args = parser.parse_args()

    project = args.project.resolve()
    if not (project / "package.json").exists():
        print(f"[cut] {project} does not look like a cut project (no package.json)", file=sys.stderr)
        return 2

    slug = project.name[4:] if project.name.startswith("cut-") else project.name
    out_dir = project / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    duration_frames, cut_name = read_version(project, args.version)
    cut = args.cut.resolve() if args.cut else (project / "public" / cut_name)
    if not cut.exists():
        print(
            f"[cut] cut video not found: {cut}\n"
            "       Put the cut for this version in the project's public/ directory, "
            "or pass --cut.",
            file=sys.stderr,
        )
        return 2

    zone_path = out_dir / f"top-v{args.version}.mp4"
    final_path = out_dir / f"{slug}-v{args.version}.mp4"

    try:
        if not sfx_module.is_complete(project / "public"):
            sfx_module.generate(project / "public")

        if args.skip_render:
            if not zone_path.exists():
                print(f"[cut] --skip-render but {zone_path} does not exist", file=sys.stderr)
                return 2
        else:
            ensure_dependencies(project, out_dir)
            render_zone(project, args.version, zone_path, out_dir, args.render_crf)

        cut_frames = config.frame_count(cut)
        zone_frames = config.frame_count(zone_path)
        if cut_frames != zone_frames:
            print(
                f"[cut] warning: the cut has {cut_frames} frames, the zone render has "
                f"{zone_frames}. The composite stops at the shorter one, so check "
                "VERSIONS in src/timing.ts against the cut.",
                file=sys.stderr,
            )
        if duration_frames is not None and duration_frames != cut_frames:
            print(
                f"[cut] warning: timing.ts says version {args.version} is "
                f"{duration_frames} frames, the cut has {cut_frames}.",
                file=sys.stderr,
            )

        overlay(cut, zone_path, final_path, args.sfx_volume, args.crf)
        sheet = None
        if not args.no_contact_sheet:
            sheet = contact_sheet(final_path, out_dir / f"contact-v{args.version}.jpg")
    except config.MediaError as exc:
        print(f"[cut] {exc}", file=sys.stderr)
        return 1

    print(f"video:        {final_path}")
    if sheet:
        print(f"contact sheet: {sheet}")
    print(f"zone render:  {zone_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
