#!/usr/bin/env python3
"""Hook-Versionen aus dem Rohschnitt festlegen (Schritt 5).

Jede Version = eigene Hook-Clips + gemeinsamer Body (alle Clips ab --body).
Schreibt in den Schnitt-Ordner:
  bereiche.json  {v: {bereiche: [[von, bis], ...], hook}}   Rohschnitt-Frames
  meta.json      {HOOK: {v}, SATZ2: {v}, TAKE_SCHNITTE: {v: [...]}, BODY}
  woerter.json   {hook: {v: [{w, von, bis}]}, body: [{w, von, bis}]}   Frames relativ zu Hook bzw. Body

SATZ2 = Beginn des zweiten Hook-Clips (harter Schnitt nach Satz 1), bei nur
einem Hook-Clip das Hook-Ende. TAKE_SCHNITTE = alle Clip-Grenzen im Reel.

Aufruf: python versionen.py <rohschnitt-ordner> <schnitt-ordner> v1=1,2 v2=3,2 v3=4 --body 5
Clip-Nummern zählen ab 1 in der Reihenfolge von kanten.json.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FPS = 30


def berechnen(kanten: dict, woerter: list[dict], versionen: dict[str, list[int]], body_ab: int) -> tuple[dict, dict, dict]:
    clips = kanten["clips"]
    if not 1 <= body_ab <= len(clips):
        raise SystemExit(f"--body {body_ab} liegt außerhalb der {len(clips)} Clips")
    cum = [0]
    for c in clips:
        cum.append(cum[-1] + c["bisFrame"] - c["vonFrame"])

    def wortliste(nrs: list[int]) -> tuple[list[dict], int, list[int]]:
        aus, pos, schnitte = [], 0, []
        for n in nrs:
            c = clips[n - 1]
            schnitte.append(pos)
            for w in woerter:
                if w["end"] > c["von"] + 0.06 and w["start"] >= c["von"] - 0.3 and w["start"] < c["bis"] - 0.03:
                    von = pos + max(0, round((w["start"] - c["von"]) * FPS))
                    bis = pos + round((min(w["end"], c["bis"]) - c["von"]) * FPS)
                    aus.append({"w": w["wort"], "von": von, "bis": bis})
            pos += c["bisFrame"] - c["vonFrame"]
        return aus, pos, schnitte

    bw, blen, bschnitte = wortliste(list(range(body_ab, len(clips) + 1)))
    out = {"hook": {}, "body": bw}
    bereiche: dict = {}
    meta = {"BODY": blen, "HOOK": {}, "TAKE_SCHNITTE": {}, "SATZ2": {}}
    for v, nrs in versionen.items():
        if any(not 1 <= n < body_ab for n in nrs):
            raise SystemExit(f"{v}: Hook-Clips müssen vor dem Body (Clip {body_ab}) liegen, bekommen {nrs}")
        hw, hlen, hs = wortliste(nrs)
        out["hook"][v] = hw
        meta["HOOK"][v] = hlen
        meta["SATZ2"][v] = hs[1] if len(hs) > 1 else hlen
        meta["TAKE_SCHNITTE"][v] = hs[1:] + [hlen + s for s in bschnitte]
        bereiche[v] = {"bereiche": [[cum[n - 1], cum[n]] for n in nrs] + [[cum[body_ab - 1], cum[-1]]], "hook": hlen}
    return out, bereiche, meta


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rohschnitt", type=Path)
    ap.add_argument("ziel", type=Path)
    ap.add_argument("versionen", nargs="+", help="v1=1,2 v2=3,2 ...")
    ap.add_argument("--body", type=int, required=True, help="erster Body-Clip (ab 1)")
    args = ap.parse_args()
    kanten = json.loads((args.rohschnitt / "kanten.json").read_text())
    woerter = json.loads((args.rohschnitt / "woerter.json").read_text())
    versionen = {}
    for a in args.versionen:
        v, nrs = a.split("=", 1)
        versionen[v] = [int(x) for x in nrs.split(",") if x]
    out, bereiche, meta = berechnen(kanten, woerter, versionen, args.body)
    args.ziel.mkdir(parents=True, exist_ok=True)
    (args.ziel / "woerter.json").write_text(json.dumps(out, ensure_ascii=False))
    (args.ziel / "bereiche.json").write_text(json.dumps(bereiche, indent=1))
    (args.ziel / "meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta))
    print("Rohschnitt gesamt", kanten["frames"], "Frames")


if __name__ == "__main__":
    main()
