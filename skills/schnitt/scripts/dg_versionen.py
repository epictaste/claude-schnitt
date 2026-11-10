#!/usr/bin/env python3
"""Wortzeiten je Version neu von Deepgram, auf dem fertigen Versions-Ton (Schritt 5).

Die Wortzeiten aus dem Rohschnitt sind umgerechnet und können an den Kanten um
ein paar Frames danebenliegen. Für Untertitel, die exakt auf dem Wort sitzen,
wird der Ton jeder Version (<v>-neu.mp4, mit 0,5 s Stille davor) einmal
transkribiert. Schreibt <schnitt>/woerter.json neu: hook je Version, body aus
der ersten Version. Rohantworten als <v>-dg.json.

Aufruf: python dg_versionen.py <schnitt-ordner> [Keyterm ...]
Keyterms = Wörter, die Deepgram sicher erkennen soll (Produktnamen, Eigennamen).
Der Key kommt aus DEEPGRAM_API_KEY, ~/.config/schnitt/.env oder ~/.config/watch/.env.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

FPS = config.FPS
VORLAUF = 0.5


def url(keyterms: list[str]) -> str:
    teile = [("model", config.model()), ("language", config.language()), ("punctuate", "true")]
    teile += [("keyterm", k) for k in keyterms]
    return f"{config.DEEPGRAM_BASIS}?{urllib.parse.urlencode(teile)}"


def anfragen(wav: Path, keyterms: list[str]) -> dict:
    req = urllib.request.Request(url(keyterms), data=wav.read_bytes(),
                                 headers={"Authorization": f"Token {config.deepgram_key()}", "Content-Type": "audio/wav"})
    with urllib.request.urlopen(req, timeout=600) as antwort:
        return json.load(antwort)


def aufteilen(roh: dict, hook: int) -> tuple[list[dict], list[dict]]:
    ws = roh["results"]["channels"][0]["alternatives"][0].get("words") or []
    # Deepgram setzt das erste Wort manchmal in die vorgeschaltete Stille, nie vor Frame 0 zeigen.
    alle = [{"w": w.get("punctuated_word", w["word"]), "von": max(0, round((w["start"] - VORLAUF) * FPS)),
             "bis": max(1, round((w["end"] - VORLAUF) * FPS))} for w in ws]
    hook_w = [w for w in alle if w["von"] < hook]
    body_w = [{**w, "von": w["von"] - hook, "bis": w["bis"] - hook} for w in alle if w["von"] >= hook]
    return hook_w, body_w


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ziel", type=Path)
    ap.add_argument("keyterms", nargs="*")
    args = ap.parse_args()
    ziel = args.ziel
    meta = json.loads((ziel / "meta.json").read_text())
    out: dict = {"hook": {}, "body": None}
    for v, hook in meta["HOOK"].items():
        wav = ziel / f"{v}-dg.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-t", str(VORLAUF), "-i", "anullsrc=r=48000:cl=mono",
                        "-i", str(ziel / f"{v}-neu.mp4"), "-filter_complex",
                        "[1:a]aformat=channel_layouts=mono[b];[0][b]concat=n=2:v=0:a=1", "-ar", "48000", str(wav)], check=True)
        roh = anfragen(wav, args.keyterms)
        (ziel / f"{v}-dg.json").write_text(json.dumps(roh, ensure_ascii=False))
        hook_w, body_w = aufteilen(roh, hook)
        out["hook"][v] = hook_w
        if out["body"] is None:
            out["body"] = body_w
        print(v, " ".join(w["w"] for w in hook_w))
    print("BODY", " ".join(w["w"] for w in out["body"] or []))
    (ziel / "woerter.json").write_text(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
