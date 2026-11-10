"""Schnittstelle Werkzeuge ↔ Vorlage: versionen.py → geruest.py → tsc, und Cues der Vorlage → sfx_mix.py."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import FPS, SCRIPTS, SKILL

import sfx_mix  # noqa: E402
import versionen  # noqa: E402

TEMPLATE = SKILL / "template"
pytestmark = pytest.mark.skipif(
    not (TEMPLATE / "node_modules").is_dir() or shutil.which("npx") is None or not (SCRIPTS / "geruest.py").exists(),
    reason="Vorlage nicht installiert (npm ci in skills/schnitt/template) oder geruest.py fehlt",
)


@pytest.fixture
def projekt(tmp_path: Path) -> Path:
    """Projektordner schnitt-test/ mit Vorlage (node_modules verlinkt) und schnitt/{meta,woerter}.json aus versionen.py."""
    p = tmp_path / "schnitt-test"
    shutil.copytree(TEMPLATE, p / "remotion", ignore=shutil.ignore_patterns("node_modules", "out"))
    os.symlink(TEMPLATE / "node_modules", p / "remotion" / "node_modules")
    clips, woerter, pos = [], [], 0
    for i, n in enumerate([45, 60, 50, 90, 120]):
        clips.append({"von": pos / FPS, "bis": (pos + n) / FPS, "vonFrame": pos, "bisFrame": pos + n})
        for j in range(3):
            a = pos + 3 + j * (n // 3)
            woerter.append({"wort": f"Wort{i}{j}", "start": a / FPS, "end": (a + n // 3 - 4) / FPS})
        pos += n + 15
    out, bereiche, meta = versionen.berechnen({"quelle": "x.mov", "clips": clips, "frames": 365}, woerter,
                                              {"v1": [1, 2], "v2": [3]}, body_ab=4)
    (p / "schnitt").mkdir()
    (p / "schnitt" / "meta.json").write_text(json.dumps(meta))
    (p / "schnitt" / "woerter.json").write_text(json.dumps(out))
    (p / "schnitt" / "bereiche.json").write_text(json.dumps(bereiche))
    spec = {"titel": "Test", "augen_y": 1000, "kopf_y": 860, "gesicht_x": 540, "zoom": {"v1": 1.1, "v2": 1.04},
            "plakat": {"v1": ["Zeile eins", "Zeile zwei"], "v2": ["Andere Zeile"]},
            "hook_szene": {"v1": "beispiel"}, "body": [["beispiel", 0, 90, True], ["zweite", 90, 210, False]]}
    (p / "spec.json").write_text(json.dumps(spec))
    return p


def test_geruest_aus_versionen_kompiliert(projekt: Path):
    r = subprocess.run([sys.executable, str(SCRIPTS / "geruest.py"), str(projekt / "spec.json")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    reel = (projekt / "remotion" / "src" / "reel.ts").read_text()
    for name in ("FPS", "VERSIONEN", "HOOK", "SATZ2", "TAKE_SCHNITTE", "BODY_SCHNITTE", "BODY", "GESAMT", "HOOK_WOERTER",
                 "BODY_WOERTER", "BUEHNE", "VOLL", "KOPF_Y", "AUGEN_Y", "GESICHT_X", "ZOOM", "HOOK_SZENEN", "SZENEN", "VOLLBILD"):
        assert f"export const {name}" in reel, name
    tsc = subprocess.run(["npx", "tsc", "--noEmit"], cwd=projekt / "remotion", capture_output=True, text=True)
    assert tsc.returncode == 0, tsc.stdout + tsc.stderr

    # Cues der Vorlage im Format, das sfx_mix.py liest
    cues = subprocess.run(["npm", "run", "-s", "cues", "--", "v1"], cwd=projekt / "remotion", capture_output=True, text=True)
    assert cues.returncode == 0, cues.stderr
    liste = json.loads(cues.stdout)
    assert all(set(c) == {"t", "rolle", "gain"} for c in liste)
    assert all(c["rolle"] in sfx_mix.BASIS for c in liste)
