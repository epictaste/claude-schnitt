"""Schritt 2: transkript (ohne Deepgram), kanten, straffen, ausklang, raeusper_check, hd_take, takes_vorschau."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import FPS, REPO_ROOT, SCRIPTS, WOERTER, needs_ffmpeg, schreibe_wav

import ausklang  # noqa: E402
import config  # noqa: E402
import raeusper_check  # noqa: E402
import straffen  # noqa: E402
import transkript  # noqa: E402


def kanten(ordner: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / "schnitt.py"), "kanten", str(ordner), *extra],
                          capture_output=True, text=True)


# ---------------------------------------------------------------- transkript ohne Netz

def test_woerter_und_phrasen_aus_deepgram_antwort():
    roh = json.loads((REPO_ROOT / "tests" / "fixtures" / "deepgram-response.json").read_text())
    woerter = transkript.woerter_aus(roh)
    assert woerter[0] == {"wort": "Start", "start": 0.0, "end": 0.4}
    liste = transkript.phrasen(woerter, 0.5)
    assert liste[0]["text"] == "Start Here."  # Satzende trennt
    assert all(p["start"] <= p["end"] for p in liste)


def test_wiederholung_bekommt_marker():
    liste = [{"text": "So zeig ich dir das jetzt"}, {"text": "Nee, nochmal"}, {"text": "So zeig ich dir das jetzt gleich"}]
    transkript.marker_setzen(liste)
    assert liste[2]["aehnlich"] == [1]
    assert liste[1]["aehnlich"] == []


def test_deepgram_url_mit_keyterms():
    url = transkript.deepgram_url(["Claude", "Remotion"])
    assert url.startswith("https://api.deepgram.com/v1/listen?")
    assert "keyterm=Claude" in url and "keyterm=Remotion" in url
    assert "filler_words=true" in url


def test_stille_stuecke_werden_zusammengelegt():
    stille = [{"von": 1.0, "bis": 1.5}, {"von": 1.51, "bis": 2.0}, {"von": 3.0, "bis": 3.4}]
    assert transkript.stille_zusammenlegen(stille) == [{"von": 1.0, "bis": 2.0}, {"von": 3.0, "bis": 3.4}]


def test_projektordner_im_aktuellen_ordner(tmp_path: Path):
    assert config.projekt_ordner(Path("/irgendwo/IMG_1.MOV"), tmp_path) == tmp_path / "schnitt-IMG_1"


# ---------------------------------------------------------------- kanten

@needs_ffmpeg
def test_kanten_liegen_in_stille_und_ueberlappen_nicht(roh: Path):
    r = kanten(roh)
    assert r.returncode == 0, r.stdout + r.stderr
    k = json.loads((roh / "kanten.json").read_text())
    assert set(k) >= {"quelle", "clips", "frames"}
    assert len(k["clips"]) == len(WOERTER)
    for c in k["clips"]:
        assert set(c) >= {"von", "bis", "vonFrame", "bisFrame"}
        assert c["pegelOk"] is True
        assert c["vonFrame"] < c["bisFrame"]
    for a, b in zip(k["clips"], k["clips"][1:]):
        assert b["vonFrame"] >= a["bisFrame"]
    assert k["frames"] == sum(c["bisFrame"] - c["vonFrame"] for c in k["clips"])


@needs_ffmpeg
def test_kanten_bricht_bei_ueberlappung_ab(roh: Path):
    schnitt = {"clips": [{"von": 2.0, "bis": 5.0}, {"von": 4.0, "bis": 7.0}], "raus": []}
    (roh / "schnitt.json").write_text(json.dumps(schnitt))
    r = kanten(roh)
    assert r.returncode != 0
    assert "Überlappung" in (r.stdout + r.stderr)


@needs_ffmpeg
def test_kanten_kuerzt_pausen_nur_auf_ansage(roh: Path):
    # Ein Clip über drei Wörter: zwei Pausen von 1 s darin. Wortgrenzen leicht innerhalb der Töne, wie bei Deepgram.
    woerter = [{**w, "start": w["start"] + 0.05, "end": w["end"] - 0.05} for w in WOERTER]
    (roh / "woerter.json").write_text(json.dumps(woerter))
    (roh / "schnitt.json").write_text(json.dumps({"clips": [{"von": 2.0, "bis": 7.0}], "raus": []}))
    assert kanten(roh).returncode == 0
    assert len(json.loads((roh / "kanten.json").read_text())["clips"]) == 1  # Standard: Pausen bleiben
    assert kanten(roh, "--pause-max", "0.5", "--pause-rest", "0.2").returncode == 0
    k = json.loads((roh / "kanten.json").read_text())
    assert len(k["clips"]) == 3
    assert k["frames"] < 5 * FPS


# ---------------------------------------------------------------- straffen, ausklang, räuspern

@needs_ffmpeg
def test_straffen_zieht_kanten_an_die_sprache(roh: Path):
    assert kanten(roh).returncode == 0
    k = straffen.straffen(roh)
    for c, w in zip(k["clips"], WOERTER):
        assert abs(c["vonFrame"] - w["start"] * FPS) <= 2
        assert abs(c["bisFrame"] - w["end"] * FPS) <= 2


def _wav_ordner(tmp_path: Path, bloecke, clips, woerter=None) -> Path:
    o = tmp_path / "roh"
    schreibe_wav(o / "audio.wav", 6.0, bloecke)
    k = {"quelle": "x.mov", "fps": FPS, "clips": clips, "frames": sum(c["bisFrame"] - c["vonFrame"] for c in clips)}
    (o / "kanten.json").write_text(json.dumps(k))
    (o / "woerter.json").write_text(json.dumps(woerter or []))
    return o


def _clip(von: int, bis: int) -> dict:
    return {"clip": 1, "von": von / FPS, "bis": bis / FPS, "vonFrame": von, "bisFrame": bis}


def test_ausklang_holt_leises_wortende_zurueck(tmp_path: Path):
    # Sprache bis 2,0 s, danach leiser Ausklang (-48 dB) bis 2,3 s. straffen (-45 dB) schneidet bei 2,0 s.
    o = _wav_ordner(tmp_path, [(1.0, 2.0, -20), (2.0, 2.3, -48)], [_clip(28, 61), _clip(120, 150)])
    k = ausklang.ausklang(o)
    assert 68 <= k["clips"][0]["bisFrame"] <= 72
    assert k["frames"] == sum(c["bisFrame"] - c["vonFrame"] for c in k["clips"])


def test_ausklang_laesst_saubere_enden_und_meldet_lange_woerter(tmp_path: Path, capsys):
    woerter = [{"wort": "Äähm", "start": 1.0, "end": 1.9}]
    o = _wav_ordner(tmp_path, [(1.0, 2.0, -20)], [_clip(29, 61)], woerter)
    k = ausklang.ausklang(o)
    assert k["clips"][0]["bisFrame"] == 61
    assert "langes Wort" in capsys.readouterr().out


def test_raeusper_check_findet_block_vor_dem_satz(tmp_path: Path):
    # Räusperer 1,00-1,20 s, 0,4 s Stille, dann der Satz. Clip beginnt beim Räusperer.
    o = _wav_ordner(tmp_path, [(1.0, 1.2, -25), (1.6, 3.0, -20)], [_clip(30, 90)])
    treffer = raeusper_check.pruefen(o)
    assert [t["wo"] for t in treffer] == ["anfang"]


def test_raeusper_check_still_bei_sauberem_take(tmp_path: Path):
    o = _wav_ordner(tmp_path, [(1.0, 3.0, -20)], [_clip(29, 91)])
    assert raeusper_check.pruefen(o) == []


# ---------------------------------------------------------------- hd_take, takes_vorschau, ausgabe

@needs_ffmpeg
def test_hd_take_und_takes_vorschau(roh: Path):
    assert kanten(roh).returncode == 0
    r = subprocess.run([sys.executable, str(SCRIPTS / "hd_take.py"), str(roh), "--groesse", "180x320"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    k = json.loads((roh / "kanten.json").read_text())
    assert config.frame_count(roh / "schnitt-hd.mp4") == k["frames"]
    assert config.video_stream(roh / "schnitt-hd.mp4")["width"] == 180

    r = subprocess.run([sys.executable, str(SCRIPTS / "takes_vorschau.py"), str(roh)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    vorschau = roh.parent.parent / "aus" / "takes-vorschau.mp4"
    assert vorschau.exists()
    assert abs(config.duration_seconds(vorschau) - k["frames"] / FPS) < 0.15


@needs_ffmpeg
def test_ausgabe_mp4_hat_soll_frames(roh: Path):
    assert kanten(roh).returncode == 0
    r = subprocess.run([sys.executable, str(SCRIPTS / "schnitt.py"), "ausgabe", str(roh)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    k = json.loads((roh / "kanten.json").read_text())
    assert config.frame_count(roh / "schnitt.mp4") == k["frames"]


@pytest.mark.parametrize("skript", ["transkript.py", "schnitt.py", "straffen.py", "ausklang.py", "raeusper_check.py",
                                    "hd_take.py", "takes_vorschau.py"])
def test_hilfe_laeuft(skript: str):
    r = subprocess.run([sys.executable, str(SCRIPTS / skript), "--help"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip()
