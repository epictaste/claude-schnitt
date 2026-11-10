"""sfx.py und sfx_mix.py: synthetische Effekte, Ausdünnen, Riser auf dem Schnitt."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from conftest import SCRIPTS, needs_ffmpeg

import sfx  # noqa: E402
import sfx_mix  # noqa: E402


@needs_ffmpeg
def test_alle_effekte_werden_erzeugt(tmp_path: Path):
    assert sfx.is_complete(tmp_path) is False
    geschrieben = sfx.generate(tmp_path)
    assert len(geschrieben) == len(sfx.SOUNDS) - 1 + sfx.TYPE_VARIANTEN
    assert sfx.is_complete(tmp_path) is True
    assert sfx.generate(tmp_path) == []  # vorhandene bleiben


@needs_ffmpeg
def test_spitze_wird_getroffen(tmp_path: Path):
    for name in ("click", "pop", "whoosh", "riser"):
        p = sfx.bauen(name, tmp_path / f"{name}.wav", -6.0)
        assert abs(sfx.measure_peak(p) - -6.0) < 0.6, name


@needs_ffmpeg
def test_riser_laenge_ist_frei(tmp_path: Path):
    p = sfx.bauen("riser", tmp_path / "r.wav", dauer=1.25)
    assert abs(len(sfx_mix.lade(p)) / sfx.SR - 1.25) < 0.01


def test_ausduennen_kette_bleibt_einzelne_mit_abstand():
    cues = [{"t": 1.0 + 0.1 * i, "rolle": "type", "gain": 0.25} for i in range(5)]  # Kette
    cues += [{"t": 3.0, "rolle": "pop", "gain": 0.25}, {"t": 3.3, "rolle": "click", "gain": 0.5},  # zu dicht
             {"t": 5.0, "rolle": "ding", "gain": 0.25}, {"t": 6.0, "rolle": "unbekannt", "gain": 0.25}]
    aus = sfx_mix.ausduennen(cues)
    assert sum(c["rolle"] == "type" for c in aus) == 5
    einzeln = [c for c in aus if c["rolle"] != "type"]
    assert einzeln == [{"t": 3.3, "rolle": "click", "gain": 0.5}]  # lauterer gewinnt, ding und Unbekanntes fallen weg


def test_nachrichten_kette_ticks_werden_pops():
    cues = [{"t": 1.0 + 0.2 * i, "rolle": "tick" if i % 2 else "click", "gain": 0.25} for i in range(4)]
    assert {c["rolle"] for c in sfx_mix.ausduennen(cues)} == {"click", "pop"}


def test_gleichzeitige_gleiche_effekte_zaehlen_einmal():
    cues = [{"t": 2.0, "rolle": "whoosh", "gain": 0.25}] * 3
    assert len(sfx_mix.ausduennen(cues)) == 1


def test_leere_cues():
    assert sfx_mix.ausduennen([]) == []


def _rms_huelle(y: np.ndarray, fenster: float = 0.02) -> np.ndarray:
    w = int(fenster * sfx.SR)
    k = len(y) // w
    return np.sqrt((y[:k * w].reshape(k, w) ** 2).mean(axis=1))


@needs_ffmpeg
def test_riser_spitze_auf_dem_schnitt_und_whoosh_danach(tmp_path: Path):
    stimme = tmp_path / "stille.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "5",
                    str(stimme)], check=True)
    cues = tmp_path / "cues.json"
    cues.write_text(json.dumps([{"t": 4.0, "rolle": "click", "gain": 0.25}]))
    aus = tmp_path / "mix.wav"
    r = subprocess.run([sys.executable, str(SCRIPTS / "sfx_mix.py"), str(stimme), str(cues), "2.0", str(aus)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    y = sfx_mix.lade(aus, kanaele=2)
    assert abs(len(y) / sfx.SR - 5.0) < 0.01
    huelle = _rms_huelle(y.mean(axis=1))
    vor = huelle[: int(2.0 / 0.02)]
    assert abs(np.argmax(vor) * 0.02 - 2.0) <= 0.1  # Riser am lautesten kurz vor dem Schnitt
    assert huelle[int(0.3 / 0.02)] < vor.max() / 4  # und am Anfang noch leise
    assert huelle[int(2.06 / 0.02):int(2.6 / 0.02)].max() > 0  # Whoosh nach dem Schnitt
    assert huelle[int(4.0 / 0.02)] > 0  # Body-Effekt
    assert 20 * np.log10(np.abs(y).max()) <= -0.9


@needs_ffmpeg
def test_ohne_hook_kein_riser(tmp_path: Path):
    stimme = tmp_path / "stille.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "3",
                    str(stimme)], check=True)
    info = sfx_mix.mischen(stimme, [], 2.0, tmp_path / "mix.wav", mit_hook=False)
    assert info["hook"] is False
    assert np.abs(sfx_mix.lade(tmp_path / "mix.wav")).max() == 0
