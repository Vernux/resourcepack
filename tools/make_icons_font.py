#!/usr/bin/env python3
"""Generates the inline icon font `pandariamc:icons` (stdlib only): U+E300 = a gold coin, 8x8, shown behind a money amount.

Written: pack/assets/pandariamc/font/icons.json + pack/assets/pandariamc/textures/font/icons.png (8x8, one glyph).
Used by freebuild:survival's sidebar ("Konto: 10,00 <coin>"); the plugin writes the glyph in plain white so the texture keeps its colors.
Re-run after editing the grid; idempotent.
"""
import sys

from make_item_icons import ASSETS, png, write_json

PALETTE = {
    "K": (0x2B, 0x1D, 0x0A, 255),  # outline
    "Y": (0xFF, 0xC8, 0x3D, 255),  # gold
    "W": (0xFF, 0xF3, 0xB0, 255),  # highlight
    "y": (0xC9, 0x8A, 0x1B, 255),  # shade
}
COIN = [
    "..KKKK..",
    ".KYWYYK.",
    "KYWYYYyK",
    "KYWYYYyK",
    "KYYYYYyK",
    "KYYYYyyK",
    ".KyyyyK.",
    "..KKKK..",
]


def main():
    canvas = {(x, y): PALETTE[c] for y, row in enumerate(COIN) for x, c in enumerate(row) if c != "."}
    path = ASSETS / "textures" / "font" / "icons.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png(8, 8, canvas))
    write_json(ASSETS / "font" / "icons.json", {"providers": [
        {"type": "bitmap", "file": "pandariamc:font/icons.png", "ascent": 7, "height": 8, "chars": [""]}]})
    print("ok")


if __name__ == "__main__":
    sys.exit(main())
