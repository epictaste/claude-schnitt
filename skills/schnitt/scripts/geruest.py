#!/usr/bin/env python3
"""Schreibt das Gerüst eines Projekts: remotion/src/reel.ts, woerter.json, augen.json und die Szenen-Tabelle.

Aufruf:
  python3 geruest.py <spec.json> [--projekt <schnitt-ordner>] [--remotion <remotion-ordner>]

Liest <projekt>/schnitt/meta.json (HOOK, SATZ2, TAKE_SCHNITTE, BODY von versionen.py) und
<projekt>/schnitt/woerter.json (hook.<v>, body von dg_versionen.py). <projekt> ist der Ordner
schnitt-<videoname>, Standard: der Ordner, in dem spec.json liegt.

spec.json:
  {
    "titel": "kurzer Name des Videos",
    "augen_y": 1000, "kopf_y": 860, "gesicht_x": 540,     Lage im 1080x1920-Bild, Fallback ohne augen.json
    "zoom": {"v1": 1.1, "v2": 1.04},                      Body-Zoom (weit) je Version, jede Version ein eigenes Level
    "plakat": {"v1": ["Zeile 1", "Zeile 2"]},             Text-Hook je Version, Logo als [logo:datei.png]
    "hook_szene": {"v1": "name"},                         Vollbild-Szene von SATZ2 bis Hook-Ende, optional je Version
    "body": [["name", von, bis, vollbild], ...]          Szenen in Body-Frames, am besten auf Take-Schnitten
  }

Für jede Szene ohne Datei legt das Skript szenen/teil-<name>.tsx als sichtbaren Platzhalter an
und schreibt szenen/index.ts neu. Vorhandene Szenendateien bleiben unangetastet.
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

NAME = re.compile(r"^[a-z][a-z0-9-]*$")
UMLAUTE = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}


def fehler(text):
    print(f"FEHLER: {text}", file=sys.stderr)
    sys.exit(1)


def warnung(text):
    print(f"Hinweis: {text}", file=sys.stderr)


def schluessel(wort):
    """Wort als Marken-Schlüssel: klein, Umlaute ausgeschrieben, nur a-z und 0-9, Zahlen mit n davor."""
    k = wort.lower()
    for a, b in UMLAUTE.items():
        k = k.replace(a, b)
    k = re.sub(r"[^a-z0-9]", "", k)
    if k and k[0].isdigit():
        k = "n" + k
    return k


def marken(woerter, von, bis):
    """Startframe jedes Wortes ab 3 Zeichen (Zahlen immer), relativ zum Szenenstart. Doppelte Wörter bekommen 2, 3 dahinter."""
    m = {}
    for x in woerter:
        if von <= x["von"] < bis:
            k = schluessel(x["w"])
            if not k or (len(k) < 3 and not k[1:].isdigit()):
                continue
            basis, n = k, 2
            while k in m:
                k = f"{basis}{n}"
                n += 1
            m[k] = x["von"] - von
    return m


def satz(woerter, von, bis):
    return " ".join(x["w"] for x in woerter if von <= x["von"] < bis).replace("*/", "* /")


def pascal(name):
    return "".join(t[:1].upper() + t[1:] for t in name.split("-"))


def ts(wert):
    return json.dumps(wert, ensure_ascii=False)


def platzhalter(name):
    p = pascal(name)
    return f"""// Szene {name}: Platzhalter von geruest.py. Ersetzen nach referenz/regeln-grafiken.md.
// Solange dieser Platzhalter steht, zeigt die Szene ihren Namen, damit er in keinem Standbild übersehen wird.
import React from 'react';

import {{Gesperrt, Voll}} from '../bausteine';
import type {{Cue}} from '../geteilt';
import type {{Marken, SzenenProps}} from '../reel';

export const {p}Szene: React.FC<SzenenProps> = () => (
\t<Voll>
\t\t<Gesperrt groesse={{40}}>PLATZHALTER {name.upper()}</Gesperrt>
\t</Voll>
);

export const {p}Cues = (_m: Marken, _dauer: number): Cue[] => [];
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--projekt", type=Path, help="Ordner schnitt-<videoname> (Standard: Ordner der spec.json)")
    ap.add_argument("--remotion", type=Path, help="Remotion-Projekt (Standard: <projekt>/remotion)")
    a = ap.parse_args()

    if not a.spec.is_file():
        fehler(f"spec.json nicht gefunden: {a.spec}")
    spec = json.loads(a.spec.read_text(encoding="utf-8"))
    projekt = (a.projekt or a.spec.resolve().parent).resolve()
    remotion = (a.remotion or projekt / "remotion").resolve()
    src = remotion / "src"
    if not (src / "Komposition.tsx").is_file():
        fehler(f"{src} ist kein Projekt aus der Vorlage (Komposition.tsx fehlt). Erst template nach {remotion} kopieren.")
    for datei in ("meta.json", "woerter.json"):
        if not (projekt / "schnitt" / datei).is_file():
            fehler(f"{projekt / 'schnitt' / datei} fehlt. Erst versionen.py und dg_versionen.py laufen lassen.")

    meta = json.loads((projekt / "schnitt" / "meta.json").read_text(encoding="utf-8"))
    W = json.loads((projekt / "schnitt" / "woerter.json").read_text(encoding="utf-8"))
    hook, satz2, schnitte, body_len = meta["HOOK"], meta["SATZ2"], meta["TAKE_SCHNITTE"], meta["BODY"]
    V = list(hook.keys())
    if not V:
        fehler("meta.json enthält keine Version")
    for v in V:
        if v not in W.get("hook", {}):
            fehler(f"woerter.json hat keine Hook-Wörter für {v}")
        if not re.match(r"^v[0-9]+$", v):
            fehler(f"Versionsname {v} muss v1, v2, ... heißen")

    zoom = spec.get("zoom", {})
    for v in V:
        if v not in zoom:
            fehler(f"spec.json: zoom.{v} fehlt (jede Version ein eigenes Zoom-Level)")
    if len(V) > 1 and len({round(zoom[v], 3) for v in V}) < len(V):
        warnung("zwei Versionen haben dasselbe Zoom-Level. Plattformen erkennen bildgleiche Videos als Duplikat.")
    plakat = {v: list(spec.get("plakat", {}).get(v, [])) for v in V}
    hook_szene = {v: spec.get("hook_szene", {}).get(v) for v in V}
    body = spec.get("body", [])

    letzte = 0
    for eintrag in body:
        if len(eintrag) != 4:
            fehler(f"spec.json: Body-Szene {eintrag} braucht [name, von, bis, vollbild]")
        n, von, bis, _ = eintrag
        if not NAME.match(str(n)):
            fehler(f"Szenenname „{n}“: nur Kleinbuchstaben, Ziffern und Bindestrich, am Anfang ein Buchstabe")
        if not (0 <= von < bis <= body_len):
            fehler(f"Szene {n}: {von}-{bis} liegt nicht im Body (0-{body_len})")
        if von < letzte:
            fehler(f"Szene {n} beginnt bei {von}, die Szene davor endet erst bei {letzte}")
        letzte = bis
    for v, n in hook_szene.items():
        if n is not None and not NAME.match(str(n)):
            fehler(f"Hook-Szene „{n}“ ({v}): nur Kleinbuchstaben, Ziffern und Bindestrich")

    erster = V[0]
    bs = sorted({s - hook[erster] for s in schnitte[erster] if s >= hook[erster]} | {0})
    for n, von, bis, _ in body:
        for grenze in (von, bis):
            if grenze not in bs and grenze != body_len:
                warnung(f"Szene {n}: Grenze {grenze} liegt auf keinem Take-Schnitt ({bs})")

    namen = sorted({n for n in hook_szene.values() if n} | {b[0] for b in body})
    L = [
        f"// Projekt „{spec.get('titel', projekt.name)}“. Von scripts/geruest.py aus schnitt/meta.json und spec.json geschrieben, nicht von Hand ändern:",
        "// beim nächsten Lauf wird die Datei neu erzeugt. Wortzeiten in Frames, relativ zum Teil-Start.",
        "// Marken = Startframe jedes Wortes ab 3 Zeichen (Umlaute als ae/oe/ue/ss, Zahlen mit n davor, doppelte Wörter mit 2/3 dahinter), relativ zum Szenenstart.",
        "import D from './woerter.json';",
        "import {STIL} from './stil';",
        "",
        "export const FPS = 30;",
        f"export type Version = {' | '.join(repr(v) for v in V)};",
        f"export const VERSIONEN: Version[] = {ts(V)};",
        "export type Wort = {w: string; von: number; bis: number};",
        "export type Marken = Record<string, number>;",
        "",
        "/** Hook-Länge je Version (= Body-Start im Video). */",
        f"export const HOOK: Record<Version, number> = {ts(hook)};",
        "/** Erster harter Schnitt nach Satz 1: bis hier Plakat und weicher Zoom. */",
        f"export const SATZ2: Record<Version, number> = {ts(satz2)};",
        "/** Take-Schnitte je Version (Video-Frames): Untertitel wechseln mit dem Schnitt. */",
        f"export const TAKE_SCHNITTE: Record<Version, number[]> = {ts(schnitte)};",
        "/** Clip-Grenzen im Body (Body-Frames): hier wechselt der Zoom zwischen weit und nah. */",
        f"export const BODY_SCHNITTE = {ts(bs)};",
        f"export const BODY = {body_len};",
        "export const GESAMT: Record<Version, number> = {" + ", ".join(f"{v}: HOOK['{v}'] + BODY" for v in V) + "};",
        "",
        "export const HOOK_WOERTER: Record<Version, Wort[]> = {" + ", ".join(f"{v}: D.hook['{v}']" for v in V) + "};",
        "export const BODY_WOERTER: Wort[] = D.body;",
        "",
        "/** Fläche über dem Kopf und Fläche für Vollbild-Szenen, Werte aus stil.json. */",
        "export const BUEHNE = STIL.buehne;",
        "export const VOLL = STIL.voll;",
        f"export const KOPF_Y = {spec.get('kopf_y', 860)};",
        f"export const AUGEN_Y = {spec.get('augen_y', 1000)};",
        f"export const GESICHT_X = {spec.get('gesicht_x', 540)};",
        "/** Body-Zoom (weit) je Version, jede Version ein eigenes Level. Nah = weit + STIL.zoom.nahPlus. */",
        f"export const ZOOM: Record<Version, number> = {ts({v: zoom[v] for v in V})};",
        "/** Text-Hook je Version, eine Zeile pro Eintrag, Logo als [logo:datei.png]. */",
        f"export const PLAKAT: Record<Version, string[]> = {ts(plakat)};",
        "",
        f"export type SzenenName = {' | '.join(repr(n) for n in namen) if namen else 'never'};",
        "export type SzenenEintrag = {name: SzenenName; von: number; bis: number; m: Marken};",
        "export type SzenenProps = {m: Marken; dauer: number; version?: Version};",
        "",
        "/** Hook-Szene je Version: Vollbild ab SATZ2 bis Hook-Ende. Frames relativ zum Videostart. */",
        "export const HOOK_SZENEN: Record<Version, SzenenEintrag[]> = {",
    ]
    for v in V:
        n = hook_szene[v]
        a_, b_ = satz2[v], hook[v]
        if not n:
            L.append(f"\t{v}: [],")
            continue
        if b_ <= a_:
            warnung(f"{v}: Hook endet mit Satz 1 (SATZ2 = HOOK = {a_}), die Hook-Szene {n} fällt weg")
            L.append(f"\t{v}: [],")
            continue
        hw = W["hook"][v]
        L += [f"\t// {n} ({v}): „{satz(hw, a_, b_)}“",
              f"\t{v}: [{{name: '{n}', von: {a_}, bis: {b_}, m: {ts(marken(hw, a_, b_))}}}],"]
    L += ["};", "", "/** Body-Szenen, Frames relativ zum Body-Start (in allen Versionen gleich). */",
          "export const SZENEN: SzenenEintrag[] = ["]
    for n, a_, b_, voll in body:
        L += [f"\t// {n}{' (VOLLBILD)' if voll else ''}: „{satz(W['body'], a_, b_)}“",
              f"\t{{name: '{n}', von: {a_}, bis: {b_}, m: {ts(marken(W['body'], a_, b_))}}},"]
    L += ["];", "", "/** Vollbild-Passagen (Body-Frames): nur Grafik, keine Person. Im Hook: SATZ2 bis HOOK, wenn es eine Hook-Szene gibt. */",
          f"export const VOLLBILD: [number, number][] = {ts([[a_, b_] for n, a_, b_, voll in body if voll])};", ""]

    (src / "reel.ts").write_text("\n".join(L), encoding="utf-8")
    (src / "woerter.json").write_text(json.dumps(W, ensure_ascii=False), encoding="utf-8")
    augen = projekt / "schnitt" / "augen.json"
    if augen.is_file():
        shutil.copyfile(augen, src / "augen.json")
    elif not (src / "augen.json").is_file():
        (src / "augen.json").write_text("{}\n", encoding="utf-8")

    szenen = src / "szenen"
    szenen.mkdir(exist_ok=True)
    neu = []
    for n in namen:
        datei = szenen / f"teil-{n}.tsx"
        if not datei.exists():
            datei.write_text(platzhalter(n), encoding="utf-8")
            neu.append(n)
    idx = ["// Von scripts/geruest.py geschrieben: Szenenname -> [Komponente, Cues]. Nicht von Hand pflegen.",
           "import type React from 'react';", "", "import type {Cue} from '../geteilt';",
           "import type {Marken, SzenenName, SzenenProps} from '../reel';"]
    idx += [f"import {{{pascal(n)}Cues, {pascal(n)}Szene}} from './teil-{n}';" for n in namen]
    idx += ["", "export const BAUSTEIN: Record<SzenenName, [React.FC<SzenenProps>, (m: Marken, dauer: number) => Cue[]]> = {"]
    idx += [f"\t'{n}': [{pascal(n)}Szene, {pascal(n)}Cues]," for n in namen]
    idx += ["};", ""]
    (szenen / "index.ts").write_text("\n".join(idx), encoding="utf-8")

    print(f"{src / 'reel.ts'}: {len(V)} Version(en), {len(body)} Body-Szene(n), Body-Schnitte {bs}")
    if neu:
        print(f"Platzhalter angelegt: {', '.join(f'szenen/teil-{n}.tsx' for n in neu)}")


if __name__ == "__main__":
    main()
