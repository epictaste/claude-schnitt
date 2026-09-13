#!/usr/bin/env python3
"""Setup / preflight for the /cut skill.

Modes:
  setup.py --check   Silent preflight. Exit 0 if ready, 2/3/4 on failure.
  setup.py --json    Machine-readable status for the agent to parse.
  setup.py           Installer. Installs what it can, scaffolds the config file.

Design:
- Silent on success, so /cut does not print a status line on every turn.
- Idempotent: re-running never clobbers an existing config.
- Never sudo. macOS installs via brew; Linux and Windows print exact commands.
- Never writes an API key to disk automatically, only a commented placeholder.
"""
from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import config  # noqa: E402

#: ffmpeg cuts and composites, ffprobe verifies frame counts, node runs Remotion.
REQUIRED_BINARIES = ["ffmpeg", "ffprobe", "node", "npm"]

ENV_TEMPLATE = """# /cut configuration
#
# Deepgram gives word-level timestamps, which is what puts every scene change on
# a word that was actually spoken instead of a guessed time.
#
# Get a key: https://console.deepgram.com  (new accounts get free credit)
#
# If you already use the `watch` skill (github.com/epictaste/claude-eyes), your
# key in ~/.config/watch/.env is picked up automatically and you can leave this
# file alone.

DEEPGRAM_API_KEY=

# Optional overrides (defaults: model nova-3, language multi).
# `multi` covers English, German, and mixed clips. Set a single language code
# (for example en or de) for slightly better accuracy when you know it.
# CUT_DEEPGRAM_MODEL=nova-3
# CUT_DEEPGRAM_LANGUAGE=multi
"""

MIN_NODE_MAJOR = 20


def _missing_binaries() -> list[str]:
    return [b for b in REQUIRED_BINARIES if shutil.which(b) is None]


def _node_version() -> str | None:
    if shutil.which("node") is None:
        return None
    try:
        out = subprocess.run(
            ["node", "--version"], capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip().lstrip("v") or None


def _node_too_old(version: str | None) -> bool:
    if not version:
        return False
    try:
        return int(version.split(".")[0]) < MIN_NODE_MAJOR
    except ValueError:
        return False


def _warn_loose_permissions(path: Path) -> None:
    try:
        if path.stat().st_mode & 0o044:
            sys.stderr.write(
                f"[cut] WARNING: {path} is readable by other users. "
                f"Run: chmod 600 {path}\n"
            )
    except OSError:
        pass


def _scaffold_env() -> bool:
    """Create ~/.config/cut/.env with placeholders. False if it already exists."""
    if config.CONFIG_FILE.exists():
        return False
    config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config.CONFIG_FILE.write_text(ENV_TEMPLATE, encoding="utf-8")
    try:
        config.CONFIG_FILE.chmod(0o600)
    except OSError:
        pass
    return True


def _install_macos(missing: list[str]) -> tuple[bool, str]:
    if shutil.which("brew") is None:
        return False, (
            "Homebrew is not installed. Get it from https://brew.sh, then re-run setup, "
            "or install manually: brew install " + " ".join(_brew_packages(missing))
        )
    packages = _brew_packages(missing)
    if not packages:
        return True, "nothing to install"
    cmd = ["brew", "install", *packages]
    print(f"[cut] running: {' '.join(cmd)}", file=sys.stderr)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        return False, f"brew install failed with exit code {result.returncode}"
    return True, "installed via brew: " + ", ".join(packages)


def _brew_packages(missing: list[str]) -> list[str]:
    packages: list[str] = []
    for name in missing:
        pkg = "ffmpeg" if name in ("ffmpeg", "ffprobe") else name
        if pkg in ("node", "npm"):
            pkg = "node"
        if pkg not in packages:
            packages.append(pkg)
    return packages


def _hint_linux(missing: list[str]) -> str:
    hints = []
    if {"ffmpeg", "ffprobe"} & set(missing):
        hints.append("ffmpeg: sudo apt install ffmpeg  (or: sudo dnf install ffmpeg)")
    if {"node", "npm"} & set(missing):
        hints.append("node 20+: https://nodejs.org or your distro's nodesource package")
    return "\n  ".join(hints) if hints else "nothing to install"


def _hint_windows(missing: list[str]) -> str:
    hints = []
    if {"ffmpeg", "ffprobe"} & set(missing):
        hints.append("ffmpeg: winget install Gyan.FFmpeg")
    if {"node", "npm"} & set(missing):
        hints.append("node 20+: winget install OpenJS.NodeJS.LTS")
    return "\n  ".join(hints) if hints else "nothing to install"


def status() -> dict:
    """Structured preflight snapshot."""
    missing = _missing_binaries()
    key, key_file = config.api_key()
    node = _node_version()

    if missing:
        state = "needs_install_and_key" if not key else "needs_install"
    elif not key:
        state = "needs_key"
    else:
        state = "ready"

    for path in config.config_files():
        if path.exists():
            _warn_loose_permissions(path)

    return {
        "status": state,
        "can_proceed": not missing and bool(key),
        "missing_binaries": missing,
        "has_api_key": bool(key),
        "api_key_source": str(key_file) if key_file else ("environment" if key else None),
        "node_version": node,
        "node_too_old": _node_too_old(node),
        "config_file": str(config.CONFIG_FILE),
        "fallback_config_file": str(config.FALLBACK_CONFIG_FILE),
        "platform": platform.system(),
    }


def cmd_check() -> int:
    """Silent on success. 2 = binaries missing, 3 = no key, 4 = both."""
    state = status()
    if state["can_proceed"] and not state["node_too_old"]:
        return 0

    parts = []
    if state["missing_binaries"]:
        parts.append("missing: " + ", ".join(state["missing_binaries"]))
    if state["node_too_old"]:
        parts.append(f"node {state['node_version']} is older than {MIN_NODE_MAJOR}")
    if not state["has_api_key"]:
        parts.append("no DEEPGRAM_API_KEY")
    sys.stderr.write(
        f"[cut] setup incomplete ({'; '.join(parts)}). "
        f"Run: python3 {Path(__file__).resolve()}\n"
    )

    if state["missing_binaries"] and not state["has_api_key"]:
        return 4
    if state["missing_binaries"] or state["node_too_old"]:
        return 2
    return 3


def cmd_json() -> int:
    json.dump(status(), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_install() -> int:
    missing = _missing_binaries()
    if missing:
        system = platform.system()
        if system == "Darwin":
            ok, message = _install_macos(missing)
            print(f"[cut] {message}", file=sys.stderr)
            if not ok:
                return 2
            still_missing = _missing_binaries()
            if still_missing:
                print(
                    "[cut] still missing after install: " + ", ".join(still_missing),
                    file=sys.stderr,
                )
                return 2
        elif system == "Linux":
            print("[cut] dependencies missing. Install:", file=sys.stderr)
            print("  " + _hint_linux(missing), file=sys.stderr)
            return 2
        elif system == "Windows":
            print("[cut] dependencies missing. Install:", file=sys.stderr)
            print("  " + _hint_windows(missing), file=sys.stderr)
            return 2
        else:
            print(
                f"[cut] no auto-install for {system}. Missing: " + ", ".join(missing),
                file=sys.stderr,
            )
            return 2

    node = _node_version()
    if _node_too_old(node):
        print(
            f"[cut] node {node} is too old, Remotion needs {MIN_NODE_MAJOR} or newer.",
            file=sys.stderr,
        )
        return 2

    created = _scaffold_env()
    print(f"[cut] {'created' if created else 'found'} config: {config.CONFIG_FILE}")

    key, key_file = config.api_key()
    if key:
        where = key_file if key_file else "the environment"
        print(f"[cut] ready. Deepgram key found in {where}.")
        return 0

    print("")
    print("[cut] one step left: add a Deepgram API key.")
    print(f"  Edit {config.CONFIG_FILE} and set:")
    print("    DEEPGRAM_API_KEY=...")
    print("  Get a key at https://console.deepgram.com (free credit on signup).")
    print("  Without it there are no word-level timestamps, and every scene change")
    print("  would have to be guessed by hand.")
    return 3


def main() -> int:
    if len(sys.argv) > 1:
        if sys.argv[1] == "--check":
            return cmd_check()
        if sys.argv[1] == "--json":
            return cmd_json()
        print(f"unknown argument: {sys.argv[1]}", file=sys.stderr)
        return 2
    return cmd_install()


if __name__ == "__main__":
    raise SystemExit(main())
