#!/usr/bin/env python3
"""Gemeinsame Einstellungen für /schnitt.

Der Deepgram-Key kommt aus der Umgebung (DEEPGRAM_API_KEY), sonst aus
`~/.config/schnitt/.env`, sonst aus `~/.config/watch/.env`. Wer den Skill
`watch` (github.com/epictaste/claude-eyes) schon nutzt, muss nichts einrichten.

Nur Standardbibliothek. Der Key wird nie ausgegeben und nie in eine Datei geschrieben.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "schnitt"
CONFIG_FILE = CONFIG_DIR / ".env"
#: Konfiguration des Geschwister-Skills `watch`, gleicher Key.
FALLBACK_CONFIG_FILE = Path.home() / ".config" / "watch" / ".env"
#: Eigene Python-Umgebung mit numpy und pillow, legt setup.py an.
VENV_DIR = CONFIG_DIR / "venv"
#: Kompilierte Hilfsprogramme (augen), legt setup.py an.
BIN_DIR = CONFIG_DIR / "bin"

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ASSETS = SKILL_DIR / "assets"
TEMPLATE = SKILL_DIR / "template"

#: Alle Frame-Nummern in diesem Skill zählen in 30 fps.
FPS = 30

DEEPGRAM_BASIS = "https://api.deepgram.com/v1/listen"
DEFAULT_MODEL = "nova-3"
DEFAULT_LANGUAGE = "de"


def _parse_env(text: str) -> dict[str, str]:
    werte: dict[str, str] = {}
    for zeile in text.splitlines():
        roh = zeile.strip()
        if not roh or roh.startswith("#") or "=" not in roh:
            continue
        name, _, wert = roh.partition("=")
        wert = wert.strip()
        if len(wert) >= 2 and wert[0] in ('"', "'") and wert[-1] == wert[0]:
            wert = wert[1:-1]
        else:
            # Kommentar hinter einem Wert ohne Anführungszeichen abschneiden,
            # ein '#' mitten im Wert (z. B. im Key) bleibt.
            for i, ch in enumerate(wert):
                if ch == "#" and i > 0 and wert[i - 1] in " \t":
                    wert = wert[:i].rstrip()
                    break
        werte[name.strip()] = wert
    return werte


def read_env_file(pfad: Path) -> dict[str, str]:
    """dotenv-Datei lesen. Fehlt sie oder ist sie nicht lesbar: leeres dict."""
    if not pfad.exists():
        return {}
    try:
        return _parse_env(pfad.read_text(encoding="utf-8"))
    except OSError:
        return {}


def config_files() -> list[Path]:
    """Suchreihenfolge: eigene Konfiguration, dann die von watch."""
    return [CONFIG_FILE, FALLBACK_CONFIG_FILE]


def setting(name: str, default: str | None = None) -> str | None:
    """Einstellung aus der Umgebung, sonst aus den Konfigurationsdateien."""
    env = os.environ.get(name)
    if env and env.strip():
        return env.strip()
    for pfad in config_files():
        wert = read_env_file(pfad).get(name)
        if wert:
            return wert
    return default


def api_key() -> tuple[str | None, Path | None]:
    """(Deepgram-Key, Datei, aus der er kam). Aus der Umgebung: Datei None."""
    env = os.environ.get("DEEPGRAM_API_KEY")
    if env and env.strip():
        return env.strip(), None
    for pfad in config_files():
        wert = read_env_file(pfad).get("DEEPGRAM_API_KEY")
        if wert:
            return wert, pfad
    return None, None


def deepgram_key() -> str:
    """Key oder Abbruch mit Hinweis, wo er hingehört."""
    key, _ = api_key()
    if not key:
        raise SystemExit(
            f"DEEPGRAM_API_KEY fehlt. In {CONFIG_FILE} eintragen (Key gibt es auf console.deepgram.com)."
        )
    return key


def model() -> str:
    return setting("SCHNITT_DEEPGRAM_MODEL", DEFAULT_MODEL) or DEFAULT_MODEL


def language() -> str:
    return setting("SCHNITT_DEEPGRAM_LANGUAGE", DEFAULT_LANGUAGE) or DEFAULT_LANGUAGE


def venv_python() -> Path:
    return VENV_DIR / "bin" / "python"


def augen_werkzeug() -> Path:
    return BIN_DIR / "augen"


def projekt_ordner(video: Path, basis: Path | None = None) -> Path:
    """Projektordner zu einem Video: ./schnitt-<videoname> im aktuellen Ordner."""
    return (basis or Path.cwd()) / f"schnitt-{Path(video).stem}"


# --------------------------------------------------------------------------
# ffmpeg/ffprobe-Helfer
# --------------------------------------------------------------------------


class MediaError(RuntimeError):
    """Ein ffmpeg/ffprobe-Aufruf ist fehlgeschlagen. Text ist für den Nutzer gedacht."""


def run(cmd: list[str], was: str, timeout: int | None = None) -> str:
    """Befehl ausführen, stdout zurück, bei Fehler MediaError mit der letzten stderr-Zeile."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise MediaError(f"{was}: {cmd[0]} ist nicht installiert") from exc
    except subprocess.TimeoutExpired as exc:
        raise MediaError(f"{was}: {cmd[0]} nach {timeout} s abgebrochen") from exc
    if r.returncode != 0:
        zeilen = (r.stderr or "").strip().splitlines()
        raise MediaError(f"{was} fehlgeschlagen: {zeilen[-1] if zeilen else f'Exit {r.returncode}'}")
    return r.stdout


def first_int(text: str) -> int | None:
    """Erste ganze Zahl einer ffprobe-Antwort. ffprobe hängt manchmal ein leeres Feld an ("300,")."""
    m = re.search(r"\d+", text)
    return int(m.group(0)) if m else None


def frame_count(video: Path) -> int:
    """Exakte Anzahl Bilder. Dekodiert den Strom, also langsam, aber wahr."""
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
               "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", str(video)],
              f"Bilder zählen in {Path(video).name}")
    n = first_int(out)
    if n is None:
        raise MediaError(f"ffprobe liefert keine Bildzahl für {video}")
    return n


def duration_seconds(datei: Path) -> float:
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(datei)],
              f"Dauer lesen von {Path(datei).name}")
    try:
        return float(out.strip())
    except ValueError as exc:
        raise MediaError(f"ffprobe liefert keine Dauer für {datei}") from exc


def video_stream(datei: Path) -> dict:
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
               "stream=width,height,r_frame_rate,avg_frame_rate,nb_frames,color_transfer,color_primaries,color_space",
               "-of", "json", str(datei)], f"Videodaten lesen von {Path(datei).name}")
    s = json.loads(out).get("streams") or []
    if not s:
        raise MediaError(f"{datei} hat keine Videospur")
    return s[0]


def ist_hlg(datei: Path) -> bool:
    """iPhone-HDR (HLG oder PQ) muss vor dem Graden nach bt709 umgerechnet werden."""
    s = video_stream(datei)
    return s.get("color_transfer") in ("arib-std-b67", "smpte2084") or s.get("color_primaries") == "bt2020"


def write_json(pfad: Path, inhalt: object) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(inhalt, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
