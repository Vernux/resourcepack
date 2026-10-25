#!/usr/bin/env python3
"""Generates the inline icon font `pandariamc:icons` and the title font `pandariamc:logo` (stdlib only).

pandariamc:icons (8x8 glyphs in one strip, never renumber): U+E300 = gold coin (freebuild:survival's balance),
U+E301 = clock (lobby sidebar: Spielzeit), U+E302 = crown (lobby sidebar: Rang).
pandariamc:logo: U+E400 = the "PANDARIAMC" wordmark (lobby sidebar title), 5x7 letters in the network palette.
Written: pack/assets/pandariamc/font/{icons,logo}.json + textures/font/{icons,logo}.png.
The plugins write the glyphs in plain white so the textures keep their colors. Re-run after editing a grid; idempotent.
`--preview OUT.png` also writes a sheet of every glyph at 8x (a checker backdrop) to look at.
"""
import sys
from pathlib import Path

from make_item_icons import ASSETS, png, write_json

PALETTE = {
    "K": (0x2B, 0x1D, 0x0A, 255),  # outline
    "Y": (0xFF, 0xC8, 0x3D, 255),  # gold
    "W": (0xFF, 0xF3, 0xB0, 255),  # highlight
    "y": (0xC9, 0x8A, 0x1B, 255),  # shade
    "O": (0x1E, 0x1F, 0x22, 255),  # dark outline
    "F": (0xF2, 0xF3, 0xF5, 255),  # clock face
    "H": (0x72, 0x89, 0xDA, 255),  # primary (clock hands)
    "R": (0xED, 0x42, 0x45, 255),  # red gem
}
ICONS = [  # codepoint order = strip order, append only
    ("coin", [
        "..KKKK..",
        ".KYWYYK.",
        "KYWYYYyK",
        "KYWYYYyK",
        "KYYYYYyK",
        "KYYYYyyK",
        ".KyyyyK.",
        "..KKKK..",
    ]),
    ("clock", [
        "..OOOO..",
        ".OFFHFO.",
        "OFFFHFFO",
        "OFFFHFFO",
        "OFFFHHHO",
        "OFFFFFFO",
        ".OFFFFO.",
        "..OOOO..",
    ]),
    ("crown", [
        "K..KK..K",
        "KY.KK.YK",
        "KYKYYKYK",
        "KYYYYYYK",
        "KYYRRYYK",
        "KyYYYYyK",
        "KKKKKKKK",
        "........",
    ]),
]
FIRST = 0xE300

LOGO_CHAR = 0xE400
PRIMARY = (0x72, 0x89, 0xDA, 255)  # #7289DA
ACCENT = (0xFE, 0xE7, 0x5C, 255)  # #FEE75C
LETTERS = {
    "P": ["XXXX.", "X...X", "X...X", "XXXX.", "X....", "X....", "X...."],
    "A": [".XXX.", "X...X", "X...X", "XXXXX", "X...X", "X...X", "X...X"],
    "N": ["X...X", "X...X", "XX..X", "X.X.X", "X..XX", "X...X", "X...X"],
    "D": ["XXXX.", "X...X", "X...X", "X...X", "X...X", "X...X", "XXXX."],
    "R": ["XXXX.", "X...X", "X...X", "XXXX.", "X.X..", "X..X.", "X...X"],
    "I": ["XXXXX", "..X..", "..X..", "..X..", "..X..", "..X..", "XXXXX"],
    "M": ["X...X", "XX.XX", "X.X.X", "X.X.X", "X...X", "X...X", "X...X"],
    "C": [".XXX.", "X...X", "X....", "X....", "X....", "X...X", ".XXX."],
}
WORD = "PANDARIAMC"
ACCENT_FROM = 8  # "MC" in the accent color, "PANDARIA" in the primary


def logo_canvas():
    canvas = {}
    for n, letter in enumerate(WORD):
        color = ACCENT if n >= ACCENT_FROM else PRIMARY
        for y, row in enumerate(LETTERS[letter]):
            for x, c in enumerate(row):
                if c == "X":
                    canvas[(n * 6 + x, y)] = color
    return canvas, len(WORD) * 6 - 1  # letters 5 wide + 1 gap, no trailing gap


def preview(path, icons, logo):
    scale = 8
    canvas, logo_w = logo
    cells_w = max(len(ICONS) * 10 + 2, logo_w + 4)
    cells_h = 8 + 2 + 7 + 4
    sheet = {}
    for cx in range(cells_w):
        for cy in range(cells_h):
            shade = (0x31, 0x33, 0x38, 255) if (cx + cy) % 2 else (0x2B, 0x2D, 0x31, 255)
            for dx in range(scale):
                for dy in range(scale):
                    sheet[(cx * scale + dx, cy * scale + dy)] = shade

    def blit(x, y, color):
        for dx in range(scale):
            for dy in range(scale):
                sheet[(x * scale + dx, y * scale + dy)] = color

    for (x, y), color in icons.items():
        blit(1 + x // 8 * 10 + x % 8, 1 + y, color)
    for (x, y), color in canvas.items():
        blit(2 + x, 11 + y, color)
    path.write_bytes(png(cells_w * scale, cells_h * scale, sheet))


def main():
    icons = {}
    for n, (_, grid) in enumerate(ICONS):
        for y, row in enumerate(grid):
            for x, c in enumerate(row):
                if c != ".":
                    icons[(n * 8 + x, y)] = PALETTE[c]
    font_dir = ASSETS / "textures" / "font"
    font_dir.mkdir(parents=True, exist_ok=True)
    (font_dir / "icons.png").write_bytes(png(8 * len(ICONS), 8, icons))
    chars = "".join(chr(FIRST + n) for n in range(len(ICONS)))
    write_json(ASSETS / "font" / "icons.json", {"providers": [
        {"type": "bitmap", "file": "pandariamc:font/icons.png", "ascent": 7, "height": 8, "chars": [chars]}]})

    logo = logo_canvas()
    (font_dir / "logo.png").write_bytes(png(logo[1], 8, logo[0]))
    write_json(ASSETS / "font" / "logo.json", {"providers": [
        {"type": "bitmap", "file": "pandariamc:font/logo.png", "ascent": 7, "height": 8, "chars": [chr(LOGO_CHAR)]}]})
    if "--preview" in sys.argv:
        preview(Path(sys.argv[sys.argv.index("--preview") + 1]), icons, logo)
    print("ok")


if __name__ == "__main__":
    sys.exit(main())
