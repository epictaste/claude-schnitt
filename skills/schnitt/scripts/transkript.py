#!/usr/bin/env python3
"""Rohmaterial transkribieren, Stille finden, zu Phrasen packen (Schritt 2).

Holt bei Deepgram (nova-3, Füllwörter sichtbar) die Wörter mit Zeitstempeln,
cacht die Rohantwort, sucht per ffmpeg silencedetect alle stillen Stellen und
schreibt `phrasen.md`: eine Zeile pro Phrase, getrennt an jedem Satzende und
jeder Pause ab --pause Sekunden. Phrasen, die einer der drei vorherigen ähneln,
bekommen einen Marker `↻ P<nr>`. Das ist nur ein Hinweis, welcher Take bleibt,
entscheidet Claude.

Aufruf:
  transkript.py <video> [--out <ordner>] [--pause 0.5] [--keyterm Wort ...] [--neu]

Ausgabe in <ordner> (Standard: ./schnitt-<videoname>/rohschnitt/<videoname>/):
  info.json       Quelle, Dauer, fps, Auflösung
  audio.wav       Mono 16 kHz, nur für Deepgram und die Pegelmessung, nie als Ausgabe-Ton
  deepgram.json   Rohantwort, wird nur mit --neu neu geholt
  woerter.json    [{wort, start, end}] in Sekunden
  stille.json     [{von, bis}] stille Stellen unter -35 dB ab 0,15 s
  phrasen.md      Lesefassung für die Take-Auswahl

Der Deepgram-Key kommt aus DEEPGRAM_API_KEY, ~/.config/schnitt/.env oder
~/.config/watch/.env. Hochgeladen wird nur audio.wav, an Deepgram.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

STILLE_DB = -35
STILLE_MIN = 0.15
#: Zwei Stille-Stücke mit kürzerer Lücke gelten als eins (sonst entstehen beim Kürzen Schnipsel).
STILLE_LUECKE = 0.02
AEHNLICH_AB = 0.75


def deepgram_url(keyterms: list[str] | None = None) -> str:
    teile = [("model", config.model()), ("language", config.language()), ("punctuate", "true"),
             ("filler_words", "true"), ("utterances", "true")]
    teile += [("keyterm", k) for k in keyterms or []]
    return f"{config.DEEPGRAM_BASIS}?{urllib.parse.urlencode(teile)}"


def video_info(video: Path) -> dict:
    roh = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,r_frame_rate,nb_frames:format=duration", "-of", "json", str(video)],
        check=True, capture_output=True, text=True,
    ).stdout
    d = json.loads(roh)
    s = d["streams"][0]
    zaehler, nenner = s["r_frame_rate"].split("/")
    stat = video.stat()
    return {
        "quelle": str(video),
        "dauer": round(float(d["format"]["duration"]), 3),
        "fps": round(int(zaehler) / int(nenner), 3),
        "breite": s["width"],
        "hoehe": s["height"],
        "frames": int(s.get("nb_frames") or 0),
        "groesse": stat.st_size,
        "geaendert": int(stat.st_mtime),
    }


def audio_extrahieren(video: Path, ziel: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000",
         "-c:a", "pcm_s16le", str(ziel)],
        check=True,
    )


def transkribieren(audio: Path, keyterms: list[str] | None = None) -> dict:
    anfrage = urllib.request.Request(
        deepgram_url(keyterms),
        data=audio.read_bytes(),
        headers={"Authorization": f"Token {config.deepgram_key()}", "Content-Type": "audio/wav"},
    )
    with urllib.request.urlopen(anfrage, timeout=900) as antwort:
        return json.load(antwort)


def stille_finden(audio: Path) -> list[dict]:
    log = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(audio), "-af",
         f"silencedetect=noise={STILLE_DB}dB:d={STILLE_MIN}", "-f", "null", "-"],
        capture_output=True, text=True,
    ).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
    enden = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    return stille_zusammenlegen([{"von": round(a, 3), "bis": round(b, 3)} for a, b in zip(starts, enden)])


def stille_zusammenlegen(stille: list[dict], luecke: float = STILLE_LUECKE) -> list[dict]:
    """Stille-Stücke mit einer Lücke unter `luecke` Sekunden zu einem zusammenfassen."""
    aus: list[dict] = []
    for s in stille:
        if aus and s["von"] - aus[-1]["bis"] < luecke:
            aus[-1]["bis"] = max(aus[-1]["bis"], s["bis"])
        else:
            aus.append(dict(s))
    return aus


def woerter_aus(roh: dict) -> list[dict]:
    alle = roh["results"]["channels"][0]["alternatives"][0].get("words") or []
    if not alle:
        sys.exit("Deepgram hat keine Wörter geliefert, Abbruch.")
    return [
        {"wort": w.get("punctuated_word", w["word"]), "start": round(w["start"], 3), "end": round(w["end"], 3)}
        for w in alle
    ]


def phrasen(woerter: list[dict], pause: float) -> list[dict]:
    """Neue Phrase bei Pause ab `pause` oder nach einem Satzende."""
    gruppen: list[list[dict]] = []
    for w in woerter:
        satzende = gruppen and gruppen[-1][-1]["wort"].endswith((".", "?", "!"))
        if gruppen and not satzende and w["start"] - gruppen[-1][-1]["end"] < pause:
            gruppen[-1].append(w)
        else:
            gruppen.append([w])
    return [
        {"start": g[0]["start"], "end": g[-1]["end"], "text": " ".join(w["wort"] for w in g)}
        for g in gruppen
    ]


def normal(text: str) -> list[str]:
    return re.sub(r"[^\wäöüß ]", "", text.lower()).split()


def aehnlichkeit(a: str, b: str) -> float:
    wa, wb = normal(a), normal(b)
    if not wa or not wb:
        return 0.0
    ganz = difflib.SequenceMatcher(None, wa, wb).ratio()
    if min(len(wa), len(wb)) < 4:
        return ganz
    # Beim Wiederholen wird oft umformuliert, Satzanfang oder Satzende bleiben aber gleich.
    anfang = difflib.SequenceMatcher(None, wa[:4], wb[:4]).ratio()
    ende = difflib.SequenceMatcher(None, wa[-4:], wb[-4:]).ratio()
    return max(ganz, anfang, ende)


def marker_setzen(liste: list[dict]) -> None:
    for i, p in enumerate(liste):
        treffer = [j + 1 for j in range(max(0, i - 3), i) if aehnlichkeit(liste[j]["text"], p["text"]) >= AEHNLICH_AB]
        p["aehnlich"] = treffer


def zeit(s: float) -> str:
    m, rest = divmod(s, 60)
    return f"{int(m):02d}:{rest:05.2f}"


def phrasen_md(info: dict, liste: list[dict], pause: float) -> str:
    zeilen = [
        f"# Phrasen: {Path(info['quelle']).name}",
        "",
        f"Dauer {zeit(info['dauer'])}, {info['breite']}×{info['hoehe']}, {info['fps']} fps.",
        f"Getrennt an Satzenden und Pausen ab {pause} s. Format: `P<nr> [von–bis] (Pause davor) ↻ ähnlich wie … · Text`.",
        "Zeiten in mm:ss.hh, für schnitt.json in Sekunden umrechnen oder die Wortzeiten aus woerter.json nehmen.",
        "",
    ]
    vorher = 0.0
    for i, p in enumerate(liste, 1):
        luecke = p["start"] - vorher
        marker = f"↻ {', '.join(f'P{n}' for n in p['aehnlich'])} · " if p["aehnlich"] else ""
        zeilen.append(f"P{i} [{zeit(p['start'])}–{zeit(p['end'])}] ({luecke:.1f}s) {marker}{p['text']}")
        vorher = p["end"]
    return "\n".join(zeilen) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--pause", type=float, default=0.5)
    ap.add_argument("--keyterm", action="append", default=[], help="Wort, das Deepgram sicher erkennen soll (mehrfach möglich)")
    ap.add_argument("--neu", action="store_true", help="Deepgram neu abfragen statt Cache")
    args = ap.parse_args()

    video = args.video.resolve()
    if not video.exists():
        sys.exit(f"Video nicht gefunden: {video}")
    out = (args.out or config.projekt_ordner(video) / "rohschnitt" / video.stem).resolve()
    out.mkdir(parents=True, exist_ok=True)

    info = video_info(video)
    alt = out / "info.json"
    if alt.exists() and not args.neu:
        vorher = json.loads(alt.read_text())
        if (vorher.get("groesse"), vorher.get("geaendert")) != (info["groesse"], info["geaendert"]):
            print("Quelle hat sich geändert (gleicher Name, andere Datei), Cache wird verworfen")
            args.neu = True
    alt.write_text(json.dumps(info, ensure_ascii=False, indent=1))

    audio = out / "audio.wav"
    if not audio.exists() or args.neu:
        audio_extrahieren(video, audio)

    cache = out / "deepgram.json"
    if cache.exists() and not args.neu:
        print("Deepgram: Cache")
        roh = json.loads(cache.read_text())
    else:
        print("Deepgram: neu transkribiert")
        roh = transkribieren(audio, args.keyterm)
        cache.write_text(json.dumps(roh, ensure_ascii=False))

    woerter = woerter_aus(roh)
    (out / "woerter.json").write_text(json.dumps(woerter, ensure_ascii=False, indent=1))
    stille = stille_finden(audio)
    (out / "stille.json").write_text(json.dumps(stille, indent=1))
    liste = phrasen(woerter, args.pause)
    marker_setzen(liste)
    (out / "phrasen.md").write_text(phrasen_md(info, liste, args.pause))
    print(f"{len(woerter)} Wörter, {len(liste)} Phrasen, {len(stille)} stille Stellen → {out}")
    erwartet = info["dauer"] * info["fps"]
    vfr = info["frames"] and abs(info["frames"] - erwartet) > max(2, erwartet * 0.005)
    if abs(info["fps"] - 30) > 0.01 or vfr:
        print(f"Achtung: {info['fps']} fps{' (variabel)' if vfr else ''}. hd_take.py rechnet auf 30 fps um, "
              "schnitt.py ausgabe --mp4 erwartet konstante 30 fps (vorher umwandeln).")


if __name__ == "__main__":
    main()
