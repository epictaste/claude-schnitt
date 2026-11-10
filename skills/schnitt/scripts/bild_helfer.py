"""Kleine Bild-Helfer für Kontaktbögen (pillow)."""
from __future__ import annotations

from PIL import ImageFont

SCHRIFTEN = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def schrift(groesse: int):
    for pfad in SCHRIFTEN:
        try:
            return ImageFont.truetype(pfad, groesse)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=groesse)
    except TypeError:  # pillow vor 10.1
        return ImageFont.load_default()
