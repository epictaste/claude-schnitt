"""setup.py, config.py und der SessionStart-Hook: die Teile, die die Umgebung anfassen."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from conftest import REPO_ROOT, SCRIPTS

import config  # noqa: E402
import setup as setup_script  # noqa: E402


def test_status_ist_json_und_vollstaendig():
    s = setup_script.status()
    assert s["status"] in {"ready", "needs_install", "needs_key", "needs_install_and_key"}
    assert {"venv_ok", "augen_ok", "template_ok", "missing_binaries", "has_api_key"} <= set(s)
    json.dumps(s)


def test_status_zeigt_den_key_nie():
    key, _ = config.api_key()
    if key:
        assert key not in json.dumps(setup_script.status())


def _ohne_key_env(tmp_path: Path) -> dict:
    env = {k: v for k, v in os.environ.items() if k != "DEEPGRAM_API_KEY"}
    env["HOME"] = str(tmp_path)
    return env


def test_json_modus_laeuft():
    r = subprocess.run([sys.executable, str(SCRIPTS / "setup.py"), "--json"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "can_proceed" in json.loads(r.stdout)


def test_check_meldet_fehlenden_key(tmp_path: Path):
    r = subprocess.run([sys.executable, str(SCRIPTS / "setup.py"), "--check"], capture_output=True, text=True,
                       env=_ohne_key_env(tmp_path))
    assert r.returncode in (3, 4)
    assert "DEEPGRAM_API_KEY" in r.stderr


def test_key_aus_watch_als_rueckfall(tmp_path: Path):
    watch = tmp_path / ".config" / "watch"
    watch.mkdir(parents=True)
    wert = "test-nur-fuer-pytest"
    (watch / ".env").write_text(f"DEEPGRAM_API_KEY={wert}\n")
    code = ("import config, json; k, q = config.api_key(); print(json.dumps([k == 'test-nur-fuer-pytest', str(q)]))")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=_ohne_key_env(tmp_path),
                       cwd=SCRIPTS)
    ok, quelle = json.loads(r.stdout)
    assert ok and quelle.endswith("watch/.env")


def test_eigene_konfiguration_gewinnt(tmp_path: Path):
    for name, wert in (("schnitt", "eigener"), ("watch", "fremder")):
        d = tmp_path / ".config" / name
        d.mkdir(parents=True)
        (d / ".env").write_text(f"DEEPGRAM_API_KEY={wert}\n")
    code = "import config; print(config.api_key()[0])"
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=_ohne_key_env(tmp_path), cwd=SCRIPTS)
    assert r.stdout.strip() == "eigener"


def test_env_parsing():
    werte = config._parse_env("\n".join(["# Kommentar", "PLAIN=wert", "QUOTED='bleibt so'", "KOMMENTIERT=wert  # Notiz",
                                         "HASH=abc#123", "kaputte zeile"]))
    assert werte == {"PLAIN": "wert", "QUOTED": "bleibt so", "KOMMENTIERT": "wert", "HASH": "abc#123"}


def test_first_int_uebersteht_ffprobes_komma():
    assert config.first_int("300,\n") == 300
    assert config.first_int("\n") is None
    assert config.first_int("N/A") is None


def test_hook_bleibt_still_oder_eine_zeile(tmp_path: Path):
    r = subprocess.run(["bash", str(REPO_ROOT / "hooks" / "scripts" / "check-setup.sh")], capture_output=True, text=True,
                       env=_ohne_key_env(tmp_path))
    assert r.returncode == 0
    assert len(r.stdout.strip().splitlines()) <= 1
    assert r.stdout.startswith("/schnitt:")


def test_hooks_json_zeigt_auf_das_skript():
    hooks = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text())
    befehl = hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    assert befehl.endswith("hooks/scripts/check-setup.sh")
    assert (REPO_ROOT / "hooks" / "scripts" / "check-setup.sh").exists()
