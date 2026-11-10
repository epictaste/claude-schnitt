#!/usr/bin/env python3
"""Erzeugt assets/hlg709.cube: iPhone-HDR (HLG, BT.2020) nach SDR (BT.709) als 3D-LUT.

Die LUT ist im Repo mitgeliefert. Dieses Skript zeigt, wie sie entsteht, und baut sie bei Bedarf neu.
Nur Standardbibliothek.

Rechenweg je Gitterpunkt (Eingang R'G'B' in BT.2020, Vollbereich 0 bis 1, so wie hd_take.py und
schnitt.py sie nach `scale=in_color_matrix=bt2020,format=gbrp16le` an lut3d geben):

1. Anzeige-Licht wie auf einem SDR-Monitor: L = V ** 2.4 (BT.1886). HLG ist so gebaut, dass das
   Signal auf einem SDR-Bildschirm direkt richtig aussieht (ITU-R BT.2390), Grau bleibt also Grau
   in derselben Helligkeit.
2. Farbraum BT.2020 nach BT.709 im linearen Licht (Matrix aus ITU-R BT.2087).
3. Was außerhalb von BT.709 liegt, wird auf 0 bis 1 begrenzt.
4. Zurück ins Signal: V = L ** (1 / 2.4).

Aufruf: python hlg_lut.py [ziel.cube] [--groesse 33]
Standard-Ziel: assets/hlg709.cube neben diesem Skript-Ordner.
"""
from __future__ import annotations

import argparse
from pathlib import Path

GAMMA = 2.4
#: Lineares BT.2020-RGB nach linearem BT.709-RGB (ITU-R BT.2087, Abschnitt 2).
BT2020_NACH_709 = (
    (1.6605, -0.5876, -0.0728),
    (-0.1246, 1.1329, -0.0083),
    (-0.0182, -0.1006, 1.1187),
)


def punkt(r: float, g: float, b: float) -> tuple[float, float, float]:
    lin = (r ** GAMMA, g ** GAMMA, b ** GAMMA)
    aus = []
    for zeile in BT2020_NACH_709:
        wert = sum(k * x for k, x in zip(zeile, lin))
        aus.append(min(1.0, max(0.0, wert)) ** (1 / GAMMA))
    return aus[0], aus[1], aus[2]


def lut_text(groesse: int) -> str:
    zeilen = [
        "# HLG (BT.2020) nach SDR (BT.709), erzeugt von scripts/hlg_lut.py",
        'TITLE "hlg709"',
        f"LUT_3D_SIZE {groesse}",
    ]
    n = groesse - 1
    # .cube: Rot läuft am schnellsten, dann Grün, dann Blau.
    for bi in range(groesse):
        for gi in range(groesse):
            for ri in range(groesse):
                r, g, b = punkt(ri / n, gi / n, bi / n)
                zeilen.append(f"{r:.6f} {g:.6f} {b:.6f}")
    return "\n".join(zeilen) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ziel", nargs="?", type=Path,
                    default=Path(__file__).resolve().parent.parent / "assets" / "hlg709.cube")
    ap.add_argument("--groesse", type=int, default=33, help="Gitterpunkte je Achse")
    args = ap.parse_args()
    args.ziel.write_text(lut_text(args.groesse), encoding="ascii")
    print(f"{args.ziel}: {args.groesse}^3 Punkte")


if __name__ == "__main__":
    main()
