"""Schritt 5 und 6: versionen → meta.json, ton_neu, hd_take mit Versionen, dg_versionen, augen, licht, stil_bilder."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from conftest import FPS, SCRIPTS, needs_ffmpeg, synth_video

import augen_messen  # noqa: E402
import config  # noqa: E402
import dg_versionen  # noqa: E402
import licht  # noqa: E402
import plakate  # noqa: E402
import stil_bilder  # noqa: E402
import ton_neu  # noqa: E402
import versionen  # noqa: E402


def _kanten(laengen: list[int]) -> tuple[dict, list[dict]]:
    """Clips mit gegebener Länge (Frames), je 10 Frames Abstand im Original, ein Wort pro Clip."""
    clips, woerter, pos = [], [], 0
    for i, n in enumerate(laengen):
        clips.append({"clip": i + 1, "von": pos / FPS, "bis": (pos + n) / FPS, "vonFrame": pos, "bisFrame": pos + n})
        woerter.append({"wort": f"w{i + 1}", "start": (pos + 2) / FPS, "end": (pos + n - 2) / FPS})
        pos += n + 10
    return {"quelle": "x.mov", "clips": clips, "frames": sum(laengen)}, woerter


def test_meta_und_bereiche_je_version():
    k, w = _kanten([30, 40, 50, 60, 70])
    out, bereiche, meta = versionen.berechnen(k, w, {"v1": [1, 2], "v2": [3]}, body_ab=4)
    assert set(meta) == {"HOOK", "SATZ2", "TAKE_SCHNITTE", "BODY"}
    assert meta["BODY"] == 130
    assert meta["HOOK"] == {"v1": 70, "v2": 50}
    assert meta["SATZ2"] == {"v1": 30, "v2": 50}  # nur ein Hook-Clip: SATZ2 = Hook-Ende
    assert meta["TAKE_SCHNITTE"]["v1"] == [30, 70, 130]
    assert meta["TAKE_SCHNITTE"]["v2"] == [50, 110]
    assert bereiche["v1"] == {"bereiche": [[0, 30], [30, 70], [120, 250]], "hook": 70}
    assert bereiche["v2"] == {"bereiche": [[70, 120], [120, 250]], "hook": 50}
    assert set(out) == {"hook", "body"}
    assert [x["w"] for x in out["hook"]["v1"]] == ["w1", "w2"]
    assert out["hook"]["v1"][1] == {"w": "w2", "von": 32, "bis": 68}  # relativ zum Hook-Start
    assert out["body"][0] == {"w": "w4", "von": 2, "bis": 58}  # relativ zum Body-Start


def test_hook_clips_hinter_dem_body_werden_abgelehnt():
    k, w = _kanten([30, 40, 50])
    try:
        versionen.berechnen(k, w, {"v1": [3]}, body_ab=2)
    except SystemExit as e:
        assert "vor dem Body" in str(e)
    else:
        raise AssertionError("Hook-Clip im Body hätte abgelehnt werden müssen")


def test_ton_teile_folgen_den_bereichen():
    k, _ = _kanten([30, 40, 50, 60])
    assert ton_neu.teile_der_version(k["clips"], [[30, 70], [70, 180]]) == [(40, 80), (90, 140), (150, 210)]


def test_dg_versionen_teilt_hook_und_body():
    roh = {"results": {"channels": [{"alternatives": [{"words": [
        {"word": "a", "punctuated_word": "A", "start": 0.5, "end": 1.0},
        {"word": "b", "punctuated_word": "B.", "start": 1.6, "end": 2.0},
        {"word": "c", "punctuated_word": "C", "start": 3.0, "end": 3.5}]}]}]}}
    hook, body = dg_versionen.aufteilen(roh, hook=45)
    assert hook == [{"w": "A", "von": 0, "bis": 15}, {"w": "B.", "von": 33, "bis": 45}]
    assert body == [{"w": "C", "von": 30, "bis": 45}]


def test_dg_url_hat_keyterms_und_keinen_key():
    url = dg_versionen.url(["Claude"])
    assert "keyterm=Claude" in url and "Token" not in url


def test_augen_ausgabe_wird_gelesen():
    zeilen = ["/tmp/mit leerzeichen/f3.png 1100.0 600.0", "/tmp/f4.png KEIN_GESICHT", "/tmp/f5.png FEHLER", ""]
    assert augen_messen.werte_lesen(zeilen, 0.8) == [(880.0, 480.0)]


@needs_ffmpeg
def test_versionen_ton_und_hd_ende_zu_ende(roh: Path):
    assert subprocess.run([sys.executable, str(SCRIPTS / "schnitt.py"), "kanten", str(roh)], capture_output=True).returncode == 0
    schnitt = roh.parent.parent / "schnitt"
    r = subprocess.run([sys.executable, str(SCRIPTS / "versionen.py"), str(roh), str(schnitt), "v1=1,2", "v2=3", "--body", "4"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    meta = json.loads((schnitt / "meta.json").read_text())
    woerter = json.loads((schnitt / "woerter.json").read_text())
    bereiche = json.loads((schnitt / "bereiche.json").read_text())
    assert set(woerter["hook"]) == {"v1", "v2"} and woerter["body"]
    assert all(set(x) == {"w", "von", "bis"} for x in woerter["body"])

    r = subprocess.run([sys.executable, str(SCRIPTS / "ton_neu.py"), str(roh), str(schnitt)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    for v in ("v1", "v2"):
        dauer = config.duration_seconds(schnitt / f"{v}-neu.mp4")
        assert abs(dauer - (meta["HOOK"][v] + meta["BODY"]) / FPS) < 0.06

    args = [f"{v}=" + ",".join(f"{a}:{e}" for a, e in d["bereiche"]) for v, d in bereiche.items()]
    grade = schnitt / "grade.txt"
    subprocess.run([sys.executable, str(SCRIPTS / "licht.py"), "--waehle", "3", "--grade-datei", str(grade)], check=True)
    r = subprocess.run([sys.executable, str(SCRIPTS / "hd_take.py"), str(roh), *args, "--ziel", str(schnitt),
                        "--grade", str(grade), "--groesse", "180x320"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    for v in ("v1", "v2"):
        hd = schnitt / f"{v}-hd.mp4"
        assert config.frame_count(hd) == meta["HOOK"][v] + meta["BODY"]
        s = config.video_stream(hd)
        assert s["color_primaries"] == "bt709"


def test_licht_ketten_sind_gueltig():
    assert licht.kette(1).startswith("eq=brightness=-0.195")
    assert "huesaturation" in licht.kette(5)


@needs_ffmpeg
def test_licht_varianten_und_bogen(tmp_path: Path):
    video = synth_video(tmp_path / "take.mp4", 60, width=540, height=960)
    werte = licht.varianten(video, tmp_path / "vorschau", 1.0, (450, 920, 140, 200))
    assert len(werte) == 5
    assert (tmp_path / "vorschau" / "licht-bogen.jpg").exists()
    # „sehr hell“ ist heller als „kräftig“
    assert werte[4][1] > werte[0][1]


@needs_ffmpeg
def test_stil_bilder_sechs_frames_und_bogen(tmp_path: Path):
    video = synth_video(tmp_path / "referenz.mp4", 90)
    bogen = stil_bilder.bilder(video, tmp_path / "stil", 6)
    assert bogen.exists()
    assert len(list((tmp_path / "stil").glob("referenz-[0-9].jpg"))) == 6


def test_stil_zeitpunkte_ohne_raender():
    t = stil_bilder.zeitpunkte(100.0, 6)
    assert t[0] == 5.0 and t[-1] == 95.0 and len(t) == 6


def test_plakate_props_passen_zur_stilprobe():
    class A:
        plakat = ["Zeile 1", "Zeile 2"]
        untertitel = "Ein Satz"
        zoom, augen_y, gesicht_x = 1.1, 1000, 540
    p = plakate.props_fuer("plakat", A)
    assert set(p) == {"bild", "modus", "plakat", "untertitel", "zoom", "augenY", "gesichtX"}
    assert p["bild"] == "stilprobe/hook.png" and p["plakat"] == ["Zeile 1", "Zeile 2"] and p["untertitel"] == "Ein Satz"
    n = plakate.props_fuer("nah", A)
    assert n["bild"] == "stilprobe/body.png" and n["plakat"] == [] and n["untertitel"] == "Ein Satz"
