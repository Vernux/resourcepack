#!/usr/bin/env python3
"""Generates the item icons of the Zeichnen minigame's drawer (stdlib only; PNG/JSON/outline helpers from make_item_icons.py).

All under pack/assets/pandariamc/, the ids are `pandariamc:zeichnen/<name>` (a nested path is a valid id, like tastentakt/*):
  color            flat 16x16 swatch, WHITE fill: the item definition tints it with the stack's `dyed_color` component
                   (tint source `minecraft:dye`), so one model shows every RGB the plugin picks - the plugin sets the exact color.
  eraser           the eraser (hotbar slot 5)
  palette          color wheel (slot 6, opens the palette menu)
  brush_1|2|3      the brush size (slot 7): the 3x3 cell stamp, one / 2x2 (up and right, like Canvas#stamp) / 3x3 cells painted
  clear            the red-lidded bin (slot 8, "Alles löschen")
each as items/zeichnen/<name>.json + models/item/zeichnen/<name>.json (item/generated, layer0) + textures/item/zeichnen/<name>.png.

The plugin side (flag `packLook` in plugins/Zeichnen/config.json, default on) and the release steps: games/zeichnen/CLAUDE.md in the
PandariaMc repo. Re-run after editing a grid or a color; `--preview sheet.png` also writes an 8x contact sheet of all icons
(plus the swatch tinted with a few sample colors, as the client multiplies it) to look at.
"""
import colorsys
import math
import sys
from pathlib import Path

from make_item_icons import ASSETS, PALETTE, layer, png, render, write_json

# Letters for this script only (make_item_icons' PALETTE is shared by render(); the other icons never use these).
HUES = 12
PALETTE.update({"n": (205, 205, 205)})  # swatch shade: a NEUTRAL grey, so the tint only darkens, never shifts the hue
for _i in range(HUES):  # the color wheel: letters 0-9, a, b
    _r, _g, _b = colorsys.hsv_to_rgb(_i / HUES, 0.78, 0.95)
    PALETTE["0123456789ab"[_i]] = (round(_r * 255), round(_g * 255), round(_b * 255))

# the swatch is drawn white: color item * tint = exactly the tint (outline K stays almost black); the lower edge is darker
SWATCH = ["................", "..WWWWWWWWWWWW.."] + [".WWWWWWWWWWWWWn."] * 11 + [".nnnnnnnnnnnnnn.", "..nnnnnnnnnnnn..", "................"]
BIN = [
    "................",
    "......RRRR......",
    "..RRRRRRRRRRRR..",
    "..rrrrrrrrrrrr..",
    "...GGGGGGGGGG...",
    *(["...WGgGGgGGgG..."] * 8),  # grooves
    "...gggggggggg...",
    "....gggggggg....",
    "................",
]


def eraser():
    """A block eraser lying on the diagonal: blue sleeve at the bottom left, white rubber with a red worn end at the top right."""
    rows = []
    for y in range(16):
        row = ""
        for x in range(16):
            across, along = x + y - 15, x - y  # across the band (-3..3), along it (the long axis)
            if not (1 <= x <= 14 and 1 <= y <= 14 and abs(across) <= 3 and -10 <= along <= 10):
                row += "."
            elif along >= 8:
                row += "R" if across < 3 else "r"
            elif along >= -2:
                row += "G" if across == 3 else "W"
            else:
                row += "D" if across == 3 else "L" if across == -3 else "B"
        rows.append(row)
    return rows


def wheel():
    """A color wheel: 12 hue sectors around a white hub."""
    rows = []
    for y in range(16):
        row = ""
        for x in range(16):
            dx, dy = x - 7.5, 7.5 - y
            distance = math.hypot(dx, dy)
            if distance > 6.6:
                row += "."
            elif distance < 2.2:
                row += "W"
            else:
                row += "0123456789ab"[int((math.degrees(math.atan2(dy, dx)) % 360) / (360 / HUES))]
        rows.append(row)
    return rows


def brush(size):
    """The 3x3 stamp preview: cells of 4x4 px with a 1 px gap, `size` x `size` of them painted yellow (up and right of the center
    cell for even sizes, like Canvas#stamp), the rest dark."""
    low, high = -((size - 1) // 2), size // 2
    painted = {(1 + dx, 1 - dy) for dx in range(low, high + 1) for dy in range(low, high + 1)}  # (column, row), row 0 = top
    rows = ["................"]
    for cell_row in range(3):
        for pixel_row in range(4):
            row = "."
            for cell_col in range(3):
                if (cell_col, cell_row) in painted:
                    row += ("WYYY", "YYYY", "YYYy", "yyyy")[pixel_row]
                else:
                    row += "gggg"
                row += "." if cell_col < 2 else ""
            rows.append(row + ".")
        if cell_row < 2:
            rows.append("." + "." * 14 + ".")
    rows.append("................")
    return rows


ICONS = {
    "color": [layer(SWATCH)],
    "eraser": [layer(eraser())],
    "palette": [layer(wheel())],
    "brush_1": [layer(brush(1))],
    "brush_2": [layer(brush(2))],
    "brush_3": [layer(brush(3))],
    "clear": [layer(BIN)],
}
SAMPLES = [0x000000, 0xE53935, 0xFDD835, 0x43A047, 0x1E88E5, 0xFF8800, 0x8B4513, 0xFFFFFF]  # the plugin's quick colors + a few


def write_all():
    canvases = {}
    for name, layers in ICONS.items():
        canvas = render(name, layers)
        canvases[name] = canvas
        texture = ASSETS / "textures" / "item" / "zeichnen" / f"{name}.png"
        texture.parent.mkdir(parents=True, exist_ok=True)
        texture.write_bytes(png(16, 16, canvas))
        write_json(ASSETS / "models" / "item" / "zeichnen" / f"{name}.json",
                   {"parent": "minecraft:item/generated", "textures": {"layer0": f"pandariamc:item/zeichnen/{name}"}})
        model = {"type": "minecraft:model", "model": f"pandariamc:item/zeichnen/{name}"}
        if name == "color":  # tint index 0 = layer0 of item/generated; the stack's dyed_color is the tint, white without one
            model["tints"] = [{"type": "minecraft:dye", "default": -1}]
        write_json(ASSETS / "items" / "zeichnen" / f"{name}.json", {"model": model})
    print(f"{len(ICONS)} icons written to {ASSETS}")
    return canvases


def tinted(canvas, rgb):
    """What the client draws for the swatch with `rgb` as the tint: every texel times the color."""
    r, g, b = rgb >> 16 & 255, rgb >> 8 & 255, rgb & 255
    return {p: (c[0] * r // 255, c[1] * g // 255, c[2] * b // 255, c[3]) for p, c in canvas.items()}


def preview(target, canvases):
    gap, sheet = 2, {}
    for n, canvas in enumerate(canvases.values()):
        sheet.update({(x + n * (16 + gap), y): c for (x, y), c in canvas.items()})
    for n, rgb in enumerate(SAMPLES):
        sheet.update({(x + n * (16 + gap), y + 16 + gap): c for (x, y), c in tinted(canvases["color"], rgb).items()})
    w, h = max(len(canvases), len(SAMPLES)) * (16 + gap), 2 * (16 + gap)
    bg, scale = (0x36, 0x39, 0x3F, 255), 8
    full = {(x, y): sheet.get((x // scale, y // scale), bg) for y in range(h * scale) for x in range(w * scale)}
    target.write_bytes(png(w * scale, h * scale, full))
    print(f"preview: {target}")


def main():
    canvases = write_all()
    if "--preview" in sys.argv:
        preview(Path(sys.argv[sys.argv.index("--preview") + 1]), canvases)


if __name__ == "__main__":
    main()
