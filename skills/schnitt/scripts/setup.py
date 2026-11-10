#!/usr/bin/env python3
"""Einrichtung und Vorabprüfung für /schnitt (Schritt 1).

Modi:
  setup.py --check   Stille Prüfung. Exit 0 = bereit, 2 = Programme/Umgebung fehlen,
                     3 = Deepgram-Key fehlt, 4 = beides.
  setup.py --json    Zustand als JSON für Claude.
  setup.py           Einrichten: Programme (macOS per brew), Konfigurationsdatei,
                     Python-Umgebung mit numpy + pillow, Augen-Messung (swiftc),
                     Remotion-Vorlage (npm ci).

Grundsätze:
- Still bei Erfolg, damit /schnitt nicht bei jedem Schritt eine Statuszeile druckt.
- Mehrfach ausführbar, überschreibt nie eine vorhandene Konfiguration.
- Nie sudo. Unter Linux und Windows nur die genauen Befehle ausgeben.
- Schreibt nie einen Key, nur eine Vorlage mit leerem Eintrag (Rechte 0600).
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

#: ffmpeg schneidet und mischt, ffprobe zählt Bilder, node/npm rendern mit Remotion.
REQUIRED_BINARIES = ["ffmpeg", "ffprobe", "node", "npm"]
#: Pakete für die Python-Umgebung. Mehr braucht kein Skript.
VENV_PAKETE = ["numpy", "pillow"]
MIN_NODE_MAJOR = 20

ENV_TEMPLATE = """# /schnitt Konfiguration
#
# Deepgram liefert Wortzeiten. Damit liegt jeder Schnitt auf einer echten
# Sprechpause und jeder Untertitel auf dem gesprochenen Wort.
#
# Key holen: https://console.deepgram.com (neue Konten bekommen Startguthaben)
#
# Wer den Skill `watch` (github.com/epictaste/claude-eyes) nutzt: dessen Key in
# ~/.config/watch/.env wird automatisch gefunden, diese Datei kann leer bleiben.

DEEPGRAM_API_KEY=

# Optional (Standard: Modell nova-3, Sprache de). Für englische Videos: en,
# für gemischte Sprache: multi.
# SCHNITT_DEEPGRAM_MODEL=nova-3
# SCHNITT_DEEPGRAM_LANGUAGE=de
"""


def _fehlende_programme() -> list[str]:
    return [b for b in REQUIRED_BINARIES if shutil.which(b) is None]


def _node_version() -> str | None:
    if shutil.which("node") is None:
        return None
    try:
        r = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip().lstrip("v") or None


def _node_zu_alt(version: str | None) -> bool:
    if not version:
        return False
    try:
        return int(version.split(".")[0]) < MIN_NODE_MAJOR
    except ValueError:
        return False


def _rechte_warnen(pfad: Path) -> None:
    try:
        if pfad.stat().st_mode & 0o044:
            sys.stderr.write(f"[schnitt] WARNUNG: {pfad} ist für andere lesbar. Beheben: chmod 600 {pfad}\n")
    except OSError:
        pass


def _venv_ok() -> bool:
    py = config.venv_python()
    if not py.exists():
        return False
    r = subprocess.run([str(py), "-c", "import numpy, PIL"], capture_output=True)
    return r.returncode == 0


def _augen_noetig() -> bool:
    """Die Augen-Messung nutzt macOS Vision, auf anderen Systemen entfällt sie."""
    return platform.system() == "Darwin"


def _augen_ok() -> bool:
    return not _augen_noetig() or config.augen_werkzeug().exists()


def _template_ok() -> bool:
    if not (config.TEMPLATE / "package.json").exists():
        return True  # Vorlage nicht mitgeliefert, nichts zu tun
    return (config.TEMPLATE / "node_modules").is_dir()


def status() -> dict:
    fehlend = _fehlende_programme()
    key, key_datei = config.api_key()
    node = _node_version()
    umgebung = {"venv": _venv_ok(), "augen": _augen_ok(), "template": _template_ok()}
    for pfad in config.config_files():
        if pfad.exists():
            _rechte_warnen(pfad)
    if fehlend or not all(umgebung.values()):
        zustand = "needs_install_and_key" if not key else "needs_install"
    elif not key:
        zustand = "needs_key"
    else:
        zustand = "ready"
    return {
        "status": zustand,
        "can_proceed": zustand == "ready" and not _node_zu_alt(node),
        "missing_binaries": fehlend,
        "has_api_key": bool(key),
        "api_key_source": str(key_datei) if key_datei else ("environment" if key else None),
        "node_version": node,
        "node_too_old": _node_zu_alt(node),
        "venv_ok": umgebung["venv"],
        "venv_python": str(config.venv_python()),
        "augen_ok": umgebung["augen"],
        "augen": str(config.augen_werkzeug()) if _augen_noetig() else None,
        "template_ok": umgebung["template"],
        "config_file": str(config.CONFIG_FILE),
        "fallback_config_file": str(config.FALLBACK_CONFIG_FILE),
        "platform": platform.system(),
    }


def cmd_check() -> int:
    s = status()
    if s["can_proceed"]:
        return 0
    teile = []
    if s["missing_binaries"]:
        teile.append("fehlt: " + ", ".join(s["missing_binaries"]))
    if s["node_too_old"]:
        teile.append(f"node {s['node_version']} ist älter als {MIN_NODE_MAJOR}")
    if not s["venv_ok"]:
        teile.append("Python-Umgebung fehlt")
    if not s["augen_ok"]:
        teile.append("Augen-Messung nicht kompiliert")
    if not s["template_ok"]:
        teile.append("Remotion-Vorlage nicht installiert")
    if not s["has_api_key"]:
        teile.append("kein DEEPGRAM_API_KEY")
    sys.stderr.write(f"[schnitt] Einrichtung unvollständig ({'; '.join(teile)}). "
                     f"Ausführen: python3 {Path(__file__).resolve()}\n")
    installierbar = s["missing_binaries"] or s["node_too_old"] or not (s["venv_ok"] and s["augen_ok"] and s["template_ok"])
    if installierbar and not s["has_api_key"]:
        return 4
    return 2 if installierbar else 3


def cmd_json() -> int:
    json.dump(status(), sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def _brew_pakete(fehlend: list[str]) -> list[str]:
    pakete: list[str] = []
    for name in fehlend:
        p = "ffmpeg" if name in ("ffmpeg", "ffprobe") else "node"
        if p not in pakete:
            pakete.append(p)
    return pakete


def _programme_installieren(fehlend: list[str]) -> bool:
    system = platform.system()
    if system == "Darwin":
        if shutil.which("brew") is None:
            print("[schnitt] Homebrew fehlt (https://brew.sh). Danach: brew install "
                  + " ".join(_brew_pakete(fehlend)), file=sys.stderr)
            return False
        cmd = ["brew", "install", *_brew_pakete(fehlend)]
        print(f"[schnitt] führe aus: {' '.join(cmd)}", file=sys.stderr)
        if subprocess.run(cmd).returncode != 0:
            return False
        return not _fehlende_programme()
    hinweise = []
    if {"ffmpeg", "ffprobe"} & set(fehlend):
        hinweise.append("ffmpeg: sudo apt install ffmpeg" if system == "Linux" else "ffmpeg: winget install Gyan.FFmpeg")
    if {"node", "npm"} & set(fehlend):
        hinweise.append("node 20+: https://nodejs.org")
    print("[schnitt] Programme fehlen. Installieren:\n  " + "\n  ".join(hinweise), file=sys.stderr)
    return False


def _konfiguration_anlegen() -> bool:
    if config.CONFIG_FILE.exists():
        return False
    config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config.CONFIG_FILE.write_text(ENV_TEMPLATE, encoding="utf-8")
    try:
        config.CONFIG_FILE.chmod(0o600)
    except OSError:
        pass
    return True


def _venv_anlegen() -> bool:
    if _venv_ok():
        return True
    print(f"[schnitt] lege Python-Umgebung an: {config.VENV_DIR}", file=sys.stderr)
    if subprocess.run([sys.executable, "-m", "venv", str(config.VENV_DIR)]).returncode != 0:
        return False
    py = str(config.venv_python())
    r = subprocess.run([py, "-m", "pip", "install", "--quiet", "--disable-pip-version-check", *VENV_PAKETE])
    return r.returncode == 0 and _venv_ok()


def _augen_kompilieren() -> bool:
    if _augen_ok():
        return True
    if shutil.which("swiftc") is None:
        print("[schnitt] swiftc fehlt. Installieren: xcode-select --install", file=sys.stderr)
        return False
    config.BIN_DIR.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["swiftc", "-O", str(config.ASSETS / "augen.swift"), "-o", str(config.augen_werkzeug())])
    return r.returncode == 0


def _template_installieren() -> bool:
    if _template_ok():
        return True
    print(f"[schnitt] installiere Remotion-Vorlage: {config.TEMPLATE}", file=sys.stderr)
    cmd = ["npm", "ci"] if (config.TEMPLATE / "package-lock.json").exists() else ["npm", "install"]
    return subprocess.run(cmd, cwd=config.TEMPLATE).returncode == 0


def cmd_install() -> int:
    fehlend = _fehlende_programme()
    if fehlend and not _programme_installieren(fehlend):
        return 2
    node = _node_version()
    if _node_zu_alt(node):
        print(f"[schnitt] node {node} ist zu alt, Remotion braucht {MIN_NODE_MAJOR} oder neuer.", file=sys.stderr)
        return 2
    angelegt = _konfiguration_anlegen()
    print(f"[schnitt] Konfiguration {'angelegt' if angelegt else 'gefunden'}: {config.CONFIG_FILE}")
    for was, schritt in (("Python-Umgebung", _venv_anlegen), ("Augen-Messung", _augen_kompilieren),
                         ("Remotion-Vorlage", _template_installieren)):
        if not schritt():
            print(f"[schnitt] {was} konnte nicht eingerichtet werden.", file=sys.stderr)
            return 2
    key, key_datei = config.api_key()
    if key:
        print(f"[schnitt] bereit. Deepgram-Key aus {key_datei or 'der Umgebung'}. "
              f"Skripte mit numpy laufen über {config.venv_python()}.")
        return 0
    print("")
    print("[schnitt] ein Schritt fehlt noch: der Deepgram-Key.")
    print(f"  In {config.CONFIG_FILE} eintragen:")
    print("    DEEPGRAM_API_KEY=...")
    print("  Key gibt es auf https://console.deepgram.com (Startguthaben bei Anmeldung).")
    return 3


def main() -> int:
    if len(sys.argv) > 1:
        if sys.argv[1] in ("-h", "--help"):
            print(__doc__)
            return 0
        if sys.argv[1] == "--check":
            return cmd_check()
        if sys.argv[1] == "--json":
            return cmd_json()
        print(f"unbekanntes Argument: {sys.argv[1]}", file=sys.stderr)
        return 2
    return cmd_install()


if __name__ == "__main__":
    raise SystemExit(main())
