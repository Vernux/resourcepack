#!/usr/bin/env python3
"""Generates the item icons of the Zeichnen minigame's drawer (stdlib only; PNG/JSON/outline helpers from make_item_icons.py).

All under pack/assets/pandariamc/, the ids are `pandariamc:zeichnen/<name>` (a nested path is a valid id, like tastentakt/*):
  color            flat 16x16 swatch, WHITE fill: the item definition tints it with the stack's `dyed_color` component
                   (tint source `minecraft:dye`), so one model shows every RGB the plugin picks - the plugin sets the exact color.
                   The palette menu's swatches (the hotbar's Pinsel is `brush`, not this).
  brush            the Pinsel (hotbar slot 0): a paintbrush on the diagonal, handle bottom left, bristles top right, TWO layers - layer0 `brush` = handle
                   + ferrule (as drawn), layer1 `brush_paint` = only the bristle tip, drawn white like `color` and tinted by the stack's `dyed_color`
                   (item definition tints `[constant -1, dye]`, so layer0 stays as drawn and the tip shows the exact brush color).
  eraser           the eraser (hotbar slot 1)
  fill             the paint bucket (slot 2, "Füllen"): TWO layers - layer0 `fill` = the grey bucket, layer1 `fill_paint` = the paint in its opening and
                   a drip down its front, drawn white like `color` and tinted by the stack's `dyed_color` (the item definition tints layer1 only:
                   `[constant -1, dye]`, the same shape as vanilla's firework_star.json; layer0 stays as drawn), so the bucket holds the brush color.
  palette          color wheel (slot 3, opens the palette menu)
  brush_1|2|3      the brush size buttons in the palette menu: the 3x3 cell stamp, one / 2x2 (up and right, like Canvas#stamp) / 3x3 cells painted
  clear            the red-lidded bin (slot 4, "Alles löschen")
each as items/zeichnen/<name>.json + models/item/zeichnen/<name>.json (item/generated, layer0) + textures/item/zeichnen/<name>.png
(`fill` and `brush` also have layer1 + textures/item/zeichnen/<name>_paint.png).

Also the canvas font `pandariamc:zeichnen_canvas` (font/zeichnen_canvas.json + textures/font/zeichnen_canvas.png): the canvas wall is one
TextDisplay per row, every cell one glyph in its own exact RGB. The font has U+E000 = a solid white 8x8 square and U+E001 = a space glyph
with advance -1. A bitmap glyph's advance is its opaque width + 1 (client rule, BitmapProvider), so U+E000 alone would leave a 1 px gap
between cells; the plugin writes every cell as "U+E000 U+E001", and the -1 pulls the next cell back onto the square's edge: the cells
tile exactly. The codepoints and the id are mirrored in the plugin (CanvasGeometry.CELLS / FONT).

And the picker font `pandariamc:zeichnen_picker` (font/zeichnen_picker.json + textures/font/zeichnen_picker.png): the marker of the drawer's "Farbfeld"
color picker (a panel of the same text displays, ColorFieldLayout in the plugin). U+E100 = a 24x24 px ring (white, 1 px black outline on both sides,
hollow centre) = 3 cells of the picker, U+E101 = a space glyph with advance -1 (the ring is 24 px wide = advance 25, the -1 makes it 24). The ring
carries its own colors (white + black), so the plugin writes it in plain white and it reads on every color of the square and the strip.

The plugin side (the pack look is always on, there is no switch) and the release steps: games/zeichnen/CLAUDE.md in the PandariaMc repo. Re-run after editing a grid or a color; `--preview sheet.png` also writes an 8x contact sheet of all icons
(plus the swatch tinted with a few sample colors, as the client multiplies it) to look at.
"""
import colorsys
import math
import sys
from pathlib import Path

from make_item_icons import ASSETS, PALETTE, layer, pixels, png, render, write_json

# Letters for this script only (make_item_icons' PALETTE is shared by render(); the other icons never use these).
HUES = 12
PALETTE.update({"n": (205, 205, 205)})  # swatch shade: a NEUTRAL grey, so the tint only darkens, never shifts the hue
PALETTE.update({"h": (0xB0, 0x7A, 0x45), "H": (0x7E, 0x52, 0x2B)})  # the brush handle's wood, light / dark
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
# The Füllen bucket: BUCKET is layer0 (outlined by render() like every icon, the empty 10 x 3 opening of the rim), PAINT is
# layer1 (no outline, it stays inside the bucket's silhouette): the paint surface filling the opening (white over a shaded front edge) and two drips down the
# front. W / n are white / the neutral swatch grey, so texel x tint = the brush color and its shade.
BUCKET = [
    "................",
    "....gggggggg....",
    "...g........g...",
    "..gggggggggggg..",
    "..G..........g..",
    "..G..........g..",
    "..G..........g..",
    "..WWWWWWWWWWWg..",
    "..WGGGGGGGGGGg..",
    "..WGGGGGGGGGGg..",
    "..WGGGGGGGGGGg..",
    "...WGGGGGGGGg...",
    "...WGGGGGGGGg...",
    "...gggggggggg...",
    "................",
    "................",
]
PAINT = [
    "................",
    "................",
    "................",
    "................",
    "...WWWWWWWWWW...",
    "...WWWWWWWWWW...",
    "...nnnnnnnnnn...",
    ".....WW..WW.....",
    ".....WW..WW.....",
    ".....nn..WW.....",
    ".........WW.....",
    ".........nn.....",
    "................",
    "................",
    "................",
    "................",
]
# icons with a second layer: name -> the grid of layer1 (`<name>_paint`), and the tints of the item definition (index = layer)
OVERLAYS = {"fill": PAINT}
TINTS = {
    "color": [{"type": "minecraft:dye", "default": -1}],
    "fill": [{"type": "minecraft:constant", "value": -1}, {"type": "minecraft:dye", "default": -1}],
}


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


def paintbrush():
    """The Pinsel on the diagonal (bottom left to top right), as two 16x16 grids: the BODY (wooden handle + metal ferrule, layer0, as drawn) and the TIP (the
    bristles, layer1: white / neutral grey, the item definition tints it with the stack's dyed_color). Cells are tested by their distance from the centre
    line of the brush (x + y - 15 = 0) and their position along it (x - y, bottom left = negative); the width steps in along the way."""
    body, tip = [], []
    for y in range(16):
        brow, trow = "", ""
        for x in range(16):
            across, along = x + y - 15, x - y
            b = t = "."
            if 1 <= x <= 14 and 1 <= y <= 14:
                if -13 <= along <= -3 and abs(across) <= 1:  # handle, 3 cells per row
                    b = "H" if across == 1 else "h"
                elif -2 <= along <= 1 and abs(across) <= 2:  # ferrule
                    b = "g" if across == 2 else "W" if across == -2 else "G"
                elif 2 <= along <= 11:  # bristles: full width, then tapering to a point
                    half = 2 if along <= 6 else 1 if along <= 9 else 0
                    if abs(across) <= half:
                        t = "n" if across == half else "W"  # the lower right edge a shade darker
            brow += b
            trow += t
        body.append(brow)
        tip.append(trow)
    return body, tip


BRUSH_BODY, BRUSH_TIP = paintbrush()
OVERLAYS["brush"] = BRUSH_TIP  # layer1 `brush_paint`, tinted like the Füllen bucket's paint (the same [constant -1, dye] tints)
TINTS["brush"] = TINTS["fill"]


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


# the canvas font: one solid square (all texels opaque white, the text color tints it) + the -1 closing space
CANVAS_FONT_ID = "pandariamc:zeichnen_canvas"
CANVAS_GLYPH, CANVAS_CLOSE = "\ue000", "\ue001"
CANVAS_CELL = 8  # px; the font's `height` and the texture size, the plugin's CanvasGeometry.CELLS assumes advance 8 = this

# the picker font: the ring marker of the "Farbfeld" picker
PICKER_FONT_ID = "pandariamc:zeichnen_picker"
RING_GLYPH, RING_CLOSE = "\ue100", "\ue101"
RING_SIZE = 24  # px; the font's `height` and the texture size, the plugin's ColorFieldLayout.MARKER assumes advance 24 = this

ICONS = {
    "color": [layer(SWATCH)],
    "brush": [layer(BRUSH_BODY)],
    "eraser": [layer(eraser())],
    "fill": [layer(BUCKET)],
    "palette": [layer(wheel())],
    "brush_1": [layer(brush(1))],
    "brush_2": [layer(brush(2))],
    "brush_3": [layer(brush(3))],
    "clear": [layer(BIN)],
}
SAMPLES = [0x000000, 0xE53935, 0xFDD835, 0x43A047, 0x1E88E5, 0xFF8800, 0x8B4513, 0xFFFFFF]  # black (the brush's start color) + a few


def write_all():
    canvases = {}
    for name, layers in ICONS.items():
        canvas = render(name, layers)
        canvases[name] = canvas
        texture = ASSETS / "textures" / "item" / "zeichnen" / f"{name}.png"
        texture.parent.mkdir(parents=True, exist_ok=True)
        texture.write_bytes(png(16, 16, canvas))
        textures = {"layer0": f"pandariamc:item/zeichnen/{name}"}
        if name in OVERLAYS:
            paint = pixels(OVERLAYS[name], None)
            for (x, y) in list(paint):  # a dark outline round whatever of the tip / paint sticks out of layer0 (it is tinted too, so it stays near black)
                for p in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if p not in paint and p not in canvas and 0 <= p[0] < 16 and 0 <= p[1] < 16:
                        paint[p] = PALETTE["K"] + (255,)
            canvases[f"{name}_paint"] = paint
            (texture.parent / f"{name}_paint.png").write_bytes(png(16, 16, paint))
            textures["layer1"] = f"pandariamc:item/zeichnen/{name}_paint"
        write_json(ASSETS / "models" / "item" / "zeichnen" / f"{name}.json", {"parent": "minecraft:item/generated", "textures": textures})
        model = {"type": "minecraft:model", "model": f"pandariamc:item/zeichnen/{name}"}
        if name in TINTS:  # tint index = layer index of item/generated; the stack's dyed_color is the dye tint, white without one
            model["tints"] = TINTS[name]
        write_json(ASSETS / "items" / "zeichnen" / f"{name}.json", {"model": model})
    print(f"{len(ICONS)} icons ({len(OVERLAYS)} with a second layer) written to {ASSETS}")
    write_canvas_font()
    write_picker_font()
    return canvases


def write_canvas_font():
    """font/zeichnen_canvas.json + its 8x8 solid white texture (ascent 7 / height 8 = the glyph spans px 0..8 below the line top, like the
    default font's block; advance = 8 + 1 for the glyph, -1 for the closing space = 8 per cell)."""
    texture = ASSETS / "textures" / "font" / "zeichnen_canvas.png"
    texture.parent.mkdir(parents=True, exist_ok=True)
    texture.write_bytes(png(CANVAS_CELL, CANVAS_CELL, {(x, y): (255, 255, 255, 255) for x in range(CANVAS_CELL) for y in range(CANVAS_CELL)}))
    write_json(ASSETS / "font" / "zeichnen_canvas.json", {"providers": [
        {"type": "bitmap", "file": "pandariamc:font/zeichnen_canvas.png", "ascent": CANVAS_CELL - 1, "height": CANVAS_CELL, "chars": [CANVAS_GLYPH]},
        {"type": "space", "advances": {CANVAS_CLOSE: -1}},
    ]})
    print(f"font {CANVAS_FONT_ID} written to {ASSETS}")


def ring():
    """The marker: 3 px white ring, 1 px black outline outside and inside, transparent hole; the outline touches the texture's edges (the client
    trims a glyph's width to its last opaque column, so a ring that stopped short would shift the plugin's centering)."""
    centre = (RING_SIZE - 1) / 2
    pixels = {}
    for y in range(RING_SIZE):
        for x in range(RING_SIZE):
            d = math.hypot(x - centre, y - centre)
            if 8.0 <= d <= 10.9:
                pixels[(x, y)] = (255, 255, 255, 255)
            elif 7.0 <= d < 8.0 or 10.9 < d <= 11.95:
                pixels[(x, y)] = (0x1E, 0x1F, 0x22, 255)
            else:
                pixels[(x, y)] = (0, 0, 0, 0)
    return pixels


def write_picker_font():
    """font/zeichnen_picker.json + the ring texture (ascent 7 / height 24 = the glyph spans px 0..24 below the line top, like the canvas font's
    glyph but taller; advance = 24 + 1 for the glyph, -1 for the closing space = 24)."""
    texture = ASSETS / "textures" / "font" / "zeichnen_picker.png"
    texture.parent.mkdir(parents=True, exist_ok=True)
    texture.write_bytes(png(RING_SIZE, RING_SIZE, ring()))
    write_json(ASSETS / "font" / "zeichnen_picker.json", {"providers": [
        {"type": "bitmap", "file": "pandariamc:font/zeichnen_picker.png", "ascent": CANVAS_CELL - 1, "height": RING_SIZE, "chars": [RING_GLYPH]},
        {"type": "space", "advances": {RING_CLOSE: -1}},
    ]})
    print(f"font {PICKER_FONT_ID} written to {ASSETS}")


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
        bucket = {**canvases["fill"], **tinted(canvases["fill_paint"], rgb)}  # the Füllen bucket: layer1 (tinted) over layer0
        sheet.update({(x + n * (16 + gap), y + 2 * (16 + gap)): c for (x, y), c in bucket.items()})
        pinsel = {**canvases["brush"], **tinted(canvases["brush_paint"], rgb)}  # the Pinsel: the tip (layer1, tinted) over the handle
        sheet.update({(x + n * (16 + gap), y + 3 * (16 + gap)): c for (x, y), c in pinsel.items()})
    w, h = max(len(canvases), len(SAMPLES)) * (16 + gap), 4 * (16 + gap)
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
