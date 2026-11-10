"""Schritt 6: master.sh, abnahme.py (Ampel, --fix, Vollbild aus reel.ts), naht_check, vorschau.sh, bauen.sh-Syntax."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from conftest import SCRIPTS, needs_ffmpeg, needs_zsh, synth_video

import abnahme  # noqa: E402
import config  # noqa: E402
import naht_check  # noqa: E402

pytestmark = [needs_ffmpeg]

SPRECHEN = [(0.2, 1.4), (1.6, 2.9), (3.1, 4.3), (4.5, 5.8)]


def _master(tmp_path: Path, name: str, vf: str | None = None, af: str | None = None) -> Path:
    """Synthetischer 1080x1920-Render, durch master.sh gezogen. vf/af verändern den Render vorher."""
    render = synth_video(tmp_path / f"{name}-render.mp4", 180, width=1080, height=1920, toene=SPRECHEN)
    if vf or af:
        kaputt = tmp_path / f"{name}-kaputt.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(render), "-vf", vf or "null", "-af", af or "anull",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(kaputt)], check=True)
        render = kaputt
    ziel = tmp_path / "aus" / f"{name}-v1.mp4"
    ziel.parent.mkdir(exist_ok=True)
    r = subprocess.run(["zsh", str(SCRIPTS / "master.sh"), str(render), str(ziel)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return ziel


def _abnahme(master: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / "abnahme.py"), str(master), *extra], capture_output=True, text=True)


@needs_zsh
def test_master_ist_technisch_sauber(tmp_path: Path):
    m = _master(tmp_path, "sauber")
    lufs, tp = abnahme.lautheit(str(m))
    assert -15 <= lufs <= -13 and tp <= -1.0
    s = config.video_stream(m)
    assert s["color_primaries"] == "bt709" and s["color_transfer"] == "bt709"
    r = _abnahme(m)
    assert r.returncode == 0, r.stdout  # grün
    bericht = (tmp_path / "aus" / "sauber-v1-abnahme.md").read_text()
    for zeile in ("✅ **Format**", "✅ **Farbtags**", "✅ **Takt**", "✅ **Lautheit**", "✅ **Tonlöcher**", "✅ **Falsche Frames**"):
        assert zeile in bericht
    assert (tmp_path / "aus" / "sauber-v1-abnahme.jpg").exists()


@needs_zsh
def test_blitzer_zwischen_takes_ist_rot(tmp_path: Path):
    m = _master(tmp_path, "blitz", vf="drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable='eq(n,90)'")
    r = _abnahme(m)
    assert r.returncode == 1
    assert "❌ **Falsche Frames**" in r.stdout


@needs_zsh
def test_tonloch_ist_rot(tmp_path: Path):
    render = synth_video(tmp_path / "r.mp4", 180, width=1080, height=1920, toene=SPRECHEN)
    loch = tmp_path / "aus" / "loch-v1.mp4"
    loch.parent.mkdir()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(render), "-c:v", "copy",
                    "-af", "volume=enable='between(t,2.0,2.03)':volume=0", "-c:a", "aac", str(loch)], check=True)
    assert [a for a, _ in naht_check.loecher(str(loch)) if 0.1 < a < 5.9]
    r = _abnahme(loch)
    assert r.returncode == 1
    assert "❌ **Tonlöcher**" in r.stdout


@needs_zsh
def test_fix_repariert_lautheit_und_sichert_original(tmp_path: Path):
    m = _master(tmp_path, "leise")
    leiser = tmp_path / "aus" / "leise2-v1.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(m), "-c:v", "copy", "-af", "volume=-12dB", "-c:a", "aac", str(leiser)],
                   check=True)
    vorher = _abnahme(leiser)
    assert "❌ **Lautheit**" in vorher.stdout
    nachher = _abnahme(leiser, "--fix")
    assert "✅ **Lautheit**" in nachher.stdout
    assert (tmp_path / "aus" / "leise2-v1-vor-fix.mp4").exists()


def test_vollbild_aus_reel_ts(tmp_path: Path):
    (tmp_path / "remotion" / "src").mkdir(parents=True)
    (tmp_path / "remotion" / "src" / "reel.ts").write_text(
        'export const HOOK: Record<Version, number> = {"v1": 90, "v2": 120};\n'
        'export const SATZ2: Record<Version, number> = {"v1": 45, "v2": 60};\n'
        "export const HOOK_WOERTER: Record<Version, Wort[]> = {v1: D.hook.v1};\n"
        "export const VOLLBILD: [number, number][] = [[0, 30], [100, 150]];\n")
    master = tmp_path / "aus" / "video-v2.mp4"
    bereiche, quelle, zoom_ende = abnahme.vollbild_bereiche(str(master))
    assert bereiche == [(60, 120), (120, 150), (220, 270)]
    assert zoom_ende == 60 and "v2" in quelle
    assert abnahme.vollbild_bereiche(str(master), "5-10") == ([(5, 10)], "--vollbild", 0)
    assert abnahme.vollbild_bereiche(str(tmp_path / "anderswo" / "x.mp4")) == ([], None, 0)


def test_naht_check_selbsttest():
    r = subprocess.run([sys.executable, str(SCRIPTS / "naht_check.py"), "--selbsttest"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "Selbsttest ok" in r.stdout


@needs_zsh
def test_vorschau_ist_720p(tmp_path: Path):
    m = synth_video(tmp_path / "m.mp4", 30, width=1080, height=1920)
    r = subprocess.run(["zsh", str(SCRIPTS / "vorschau.sh"), str(m)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert config.video_stream(tmp_path / "m-vorschau.mp4")["width"] == 720


@needs_zsh
@pytest.mark.parametrize("skript", ["bauen.sh", "master.sh", "vorschau.sh"])
def test_shell_syntax(skript: str):
    assert subprocess.run(["zsh", "-n", str(SCRIPTS / skript)]).returncode == 0


@needs_zsh
def test_bauen_prueft_argumente(tmp_path: Path):
    r = subprocess.run(["zsh", str(SCRIPTS / "bauen.sh"), "--komposition", "Reel-v1"], capture_output=True, text=True)
    assert r.returncode == 2 and "Pflicht" in r.stderr
    r = subprocess.run(["zsh", str(SCRIPTS / "bauen.sh"), "--komposition", "Reel-v1", "--ziel", "x.mov"],
                       capture_output=True, text=True)
    assert r.returncode == 2 and ".mp4" in r.stderr
    r = subprocess.run(["zsh", str(SCRIPTS / "bauen.sh"), "--projekt", str(tmp_path), "--komposition", "Reel-v1",
                        "--ziel", str(tmp_path / "x.mp4")], capture_output=True, text=True)
    assert r.returncode == 2 and "package.json" in r.stderr
    r = subprocess.run(["zsh", str(SCRIPTS / "bauen.sh"), "--senden"], capture_output=True, text=True)
    assert r.returncode == 2
