"""Grep-Gate vor dem Veröffentlichen: keine persönlichen Pfade, Dienste oder Keys im Repo, keine Mediendateien."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from conftest import REPO_ROOT

#: Dasselbe Muster wie das Grep-Gate im Plan. In Stücken notiert, damit diese Datei sich nicht selbst findet.
MUSTER = re.compile("|".join(["ge" "org", "/Us" "ers/", "tele" "gram", "blo" "tato", "agent" "chat", "bre" "vo", "TOK" "EN=",
                              r"api[_-]?key=[A-Za-z0-9]"]), re.I)
#: Erlaubte Fundstellen: Lizenz und Autor in den Manifesten.
ERLAUBT = {"LICENSE", ".claude-plugin/plugin.json", ".claude-plugin/marketplace.json"}
OHNE = {".git", "node_modules", "__pycache__", ".pytest_cache", ".venv", "out"}


def dateien():
    for p in REPO_ROOT.rglob("*"):
        if p.is_file() and not OHNE & set(p.relative_to(REPO_ROOT).parts):
            yield p


def test_keine_persoenlichen_spuren():
    treffer = []
    for p in dateien():
        rel = p.relative_to(REPO_ROOT).as_posix()
        if rel in ERLAUBT:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for nr, zeile in enumerate(text.splitlines(), 1):
            if MUSTER.search(zeile):
                treffer.append(f"{rel}:{nr}: {zeile.strip()[:100]}")
    assert not treffer, "\n".join(treffer)


def test_keine_mediendateien_im_git():
    r = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        return  # kein Git-Checkout (z. B. Archiv), nichts zu prüfen
    medien = [f for f in r.stdout.splitlines() if re.search(r"\.(mp4|mov|mp3|wav|env)$", f, re.I)]
    assert not medien, medien
