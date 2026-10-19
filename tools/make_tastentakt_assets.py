#!/usr/bin/env python3
"""Generates the pack look of the Tastentakt minigame (stdlib only; PNG/JSON helpers from make_item_icons.py).

Item models (ItemDisplay caps), all under pack/assets/pandariamc/ - the ids are `pandariamc:tastentakt/<name>`:
  key_a|s|w|d|shift|space       the falling notes (key color filled, letter on it)
  receptor_a|s|w|d|shift|space  the caps at the bottom (dark, key colored frame and letter)
  receptor_hit, receptor_hit_wide   the white "HIT!" flash for a lane / a SHIFT-SPACE receptor
each as items/tastentakt/<name>.json + models/item/tastentakt/<name>.json (child of the shared flat two-sided quad
models/item/tastentakt/cap.json) + textures/item/tastentakt/<name>.png (60x40 lane caps, 144x40 SHIFT/SPACE caps: the
aspect of Tuning.CAP_WIDTH/SPECIAL_WIDTH : CAP_HEIGHT, the plugin scales the quad to that size, so a texel is square).
Font `pandariamc:tastentakt` (font/tastentakt.json + textures/font/tastentakt_pixel.png): the judgment popups and the combo.
Every character c is the private-use code point 0xE000 + ord(c) (PackLook#pixel in the plugin), a space is a space.

The plugin side and how to switch it on: games/tastentakt/CLAUDE.md in the PandariaMc repo. Re-run after editing a
glyph or a color; `--preview sheet.png` also writes a 2x contact sheet of all caps + font samples to look at.
"""
import sys
from pathlib import Path

from make_item_icons import ASSETS, png, write_json

# id, label, key color, letter color on a note, wide - the values of Key.java
KEYS = [
    ("a", "A", 0x2ED9F0, 0x06242A, False),
    ("s", "S", 0x3B82F6, 0xFFFFFF, False),
    ("w", "W", 0x34D17A, 0x06260F, False),
    ("d", "D", 0xDC143C, 0xFFFFFF, False),
    ("shift", "SHIFT", 0xFF9F1C, 0x2A1700, True),
    ("space", "SPACE", 0xFFD93D, 0x2A2300, True),
]
LANE, WIDE = (60, 40), (144, 40)
RADIUS = 10
FILL = 0x101418  # Board.FACE_BG
POPUP_SAMPLES = [("PERFEKT", 0x5CFFE1), ("GUT", 0x57F287), ("× DANEBEN", 0xED4245), ("x2 x4", 0xFEE75C)]

# 5x7 pixel font; the width of a glyph is its rightmost '#' (like the game does for a bitmap font). ' ' is 3 wide.
GLYPHS = {
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "N": ["#...#", "##..#", "#.#.#", "#.#.#", "#..##", "#...#", "#...#"],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"],
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["####.", "....#", "....#", ".###.", "....#", "....#", "####."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": [".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."],
    "x": [".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"],
    "×": [".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "....."],
    "!": ["#", "#", "#", "#", "#", ".", "#"],
    " ": ["...", ".", ".", ".", ".", ".", "."],
}
FONT_CHARS = "ABCDEFGHIKNPRSTUW0123456789x×!"
FONT_COLUMNS, CELL_W, CELL_H, GLYPH_SCALE = 8, 12, 16, 2
FONT_ID = "pandariamc:tastentakt"
PRIVATE_USE = 0xE000


def rgb(value, alpha=255):
    return (value >> 16 & 255, value >> 8 & 255, value & 255, alpha)


def mix(color, other, amount):
    return tuple(round(c + (o - c) * amount) for c, o in zip(color[:3], other[:3])) + (255,)


def glyph_width(char):
    return max(x for row in GLYPHS[char] for x, c in enumerate(row) if c == "#") + 1 if char != " " else 3


def text_width(text, scale):
    return (sum(glyph_width(c) for c in text) + len(text) - 1) * scale


def draw_text(canvas, text, x, y, scale, color):
    for char in text:
        for gy, row in enumerate(GLYPHS[char]):
            for gx, c in enumerate(row):
                if c == "#":
                    for dy in range(scale):
                        for dx in range(scale):
                            canvas[(x + gx * scale + dx, y + gy * scale + dy)] = color
        x += (glyph_width(char) + 1) * scale


def inside(x, y, w, h, inset):
    """Is pixel (x, y) in the rounded rectangle shrunk by `inset`?"""
    r = max(RADIUS - inset, 0)
    x0, y0, x1, y1 = inset, inset, w - inset, h - inset
    px, py = x + 0.5, y + 0.5
    if not (x0 <= px <= x1 and y0 <= py <= y1):
        return False
    cx, cy = min(max(px, x0 + r), x1 - r), min(max(py, y0 + r), y1 - r)
    return (px - cx) ** 2 + (py - cy) ** 2 <= r * r


def cap(size, rings, label, label_color, scale, top, bottom, shade=None):
    """A rounded cap: `rings` = [(inset, color)] painted outside in, the label centered between rows top..bottom,
    `shade` = (rows, color) darkens the lowest rows of the second ring, the body (a keycap's front edge)."""
    w, h = size
    canvas = {}
    for inset, color in rings:
        for y in range(h):
            for x in range(w):
                if inside(x, y, w, h, inset):
                    canvas[(x, y)] = color
    if shade:
        rows, color = shade
        for y in range(h - rows, h):
            for x in range(w):
                if inside(x, y, w, h, rings[1][0]):
                    canvas[(x, y)] = color
    draw_text(canvas, label, (w - text_width(label, scale)) // 2, top + (bottom - top - 7 * scale) // 2, scale, label_color)
    return canvas


def textures():
    """{name: (size, canvas)} of every cap, in the order notes, receptors, hit flashes."""
    out = {}
    white, black = rgb(0xFFFFFF), rgb(0)
    for name, label, color, text_color, wide in KEYS:
        key, size = rgb(color), WIDE if wide else LANE
        light = mix(key, white, 0.55)
        out[f"key_{name}"] = (size, cap(size, [(0, light), (2, key)], label, rgb(text_color), 3, 2, size[1] - 7,
                                        shade=(5, mix(key, black, 0.3))))
    for name, label, color, text_color, wide in KEYS:
        key, size = rgb(color), WIDE if wide else LANE
        out[f"receptor_{name}"] = (size, cap(size, [(0, mix(key, white, 0.55)), (2, key), (4, rgb(FILL))], label, key, 3, 4, size[1] - 4))
    for name, size, scale in (("receptor_hit", LANE, 2), ("receptor_hit_wide", WIDE, 3)):
        out[name] = (size, cap(size, [(0, rgb(0xB5BAC1)), (2, white)], "HIT!", rgb(FILL), scale, 2, size[1] - 2))
    return out


def font_sheet():
    """The glyph sheet (white texels, the text color tints them) and the font's `chars` rows."""
    cells = list(FONT_CHARS) + [None] * (-len(FONT_CHARS) % FONT_COLUMNS)
    rows = [cells[i:i + FONT_COLUMNS] for i in range(0, len(cells), FONT_COLUMNS)]
    canvas = {}
    for row, line in enumerate(rows):
        for col, char in enumerate(line):
            if char:
                draw_text(canvas, char, col * CELL_W, row * CELL_H, GLYPH_SCALE, rgb(0xFFFFFF))
    chars = ["".join(chr(PRIVATE_USE + ord(c)) if c else "\u0000" for c in line) for line in rows]
    return FONT_COLUMNS * CELL_W, len(rows) * CELL_H, canvas, chars


def write_asset(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def write_all():
    caps = textures()
    base = ASSETS / "models" / "item" / "tastentakt"
    write_json(base / "cap.json", {  # a flat quad, both sides readable from either direction; the plugin scales it
        "elements": [{
            "from": [0, 0, 8], "to": [16, 16, 8], "shade": False,
            "faces": {side: {"uv": [0, 0, 16, 16], "texture": "#layer0"} for side in ("north", "south")},
        }],
    })
    for name, ((w, h), canvas) in caps.items():
        write_asset(ASSETS / "textures" / "item" / "tastentakt" / f"{name}.png", png(w, h, canvas))
        write_json(base / f"{name}.json", {"parent": "pandariamc:item/tastentakt/cap",
                                           "textures": {"layer0": f"pandariamc:item/tastentakt/{name}"}})
        write_json(ASSETS / "items" / "tastentakt" / f"{name}.json",
                   {"model": {"type": "minecraft:model", "model": f"pandariamc:item/tastentakt/{name}"}})
    width, height, canvas, chars = font_sheet()
    write_asset(ASSETS / "textures" / "font" / "tastentakt_pixel.png", png(width, height, canvas))
    write_json(ASSETS / "font" / "tastentakt.json", {"providers": [
        {"type": "space", "advances": {" ": 4}},
        {"type": "bitmap", "file": "pandariamc:font/tastentakt_pixel.png", "ascent": 7, "height": CELL_H // GLYPH_SCALE, "chars": chars},
    ]})
    print(f"{len(caps)} caps + font {FONT_ID} ({len(FONT_CHARS)} glyphs) written to {ASSETS}")
    return caps


def preview(target, caps):
    gap, sheet = 8, {}
    y = gap
    rows = [[n for n in caps if n.startswith("key_")],
            [n for n in caps if n.startswith("receptor_") and "hit" not in n],
            [n for n in caps if "hit" in n]]
    for names in rows:
        x = gap
        for name in names:
            (w, h), canvas = caps[name]
            sheet.update({(x + px, y + py): c for (px, py), c in canvas.items()})
            x += w + gap
        y += LANE[1] + gap
    for text, color in POPUP_SAMPLES:
        draw_text(sheet, text, gap, y, GLYPH_SCALE, rgb(color))
        y += 7 * GLYPH_SCALE + gap
    w, h = max(x for x, _ in sheet) + gap + 1, y
    bg, scale = rgb(0x36393F), 2
    full = {(x, y2): sheet.get((x // scale, y2 // scale), bg) for y2 in range(h * scale) for x in range(w * scale)}
    target.write_bytes(png(w * scale, h * scale, full))
    print(f"preview: {target}")


def main():
    caps = write_all()
    if "--preview" in sys.argv:
        preview(Path(sys.argv[sys.argv.index("--preview") + 1]), caps)


if __name__ == "__main__":
    main()
