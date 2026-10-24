#!/usr/bin/env python3
"""Generates the 16x16 item icons of the PandariaMc server pack (stdlib only).

For every id in ICONS it writes
  pack/assets/pandariamc/textures/item/<id>.png   16x16 RGBA
  pack/assets/pandariamc/models/item/<id>.json    item/generated + layer0
  pack/assets/pandariamc/items/<id>.json          item definition (what `ItemBuilder#model(id)` selects)

The team_choice* icons are NOT made here (hand-made, left alone). The plugin side (id -> item): "Custom item
models" in the PandariaMc repo's CLAUDE.md. Re-run after editing a grid; `--preview sheet.png` also writes an 8x
contact sheet of all icons to look at.

Grids are 16 rows of 16 chars, letters = PALETTE, '.' = transparent. A 1px black outline is added around every
layer automatically (4-neighbour, only onto transparent pixels), so draw the fill only and leave a 1px border free.
sym="lr": rows hold the left 8 columns, mirrored; sym="quad": the top-left 8x8, mirrored both ways.
A multi-layer icon stamps its layers in order (each one outlined, so a later layer is separated from an earlier one).
"""
import json
import struct
import sys
import zlib
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "pack" / "assets" / "pandariamc"

PALETTE = {
    "K": (0x1E, 0x1F, 0x22),  # outline
    "W": (0xFF, 0xFF, 0xFF),
    "L": (0xA9, 0xB8, 0xF0),  # light primary
    "B": (0x72, 0x89, 0xDA),  # primary #7289DA
    "D": (0x4B, 0x5D, 0xA9),  # dark primary
    "G": (0xB5, 0xBA, 0xC1),  # secondary #B5BAC1
    "g": (0x80, 0x84, 0x8E),  # dark gray
    "Y": (0xFE, 0xE7, 0x5C),  # accent #FEE75C
    "y": (0xC4, 0xA9, 0x2E),  # dark accent
    "R": (0xED, 0x42, 0x45),  # error red (team red, live dot)
    "r": (0xA8, 0x2E, 0x31),
    "P": (0x91, 0x46, 0xFF),  # Twitch purple (Twitch UI only)
    "Q": (0x2A, 0x1B, 0x55),  # deep purple (screen)
}


def layer(rows, sym=None, dx=0, dy=0):
    return rows, sym, dx, dy


def bust(c):
    """A head-and-shoulders sprite, 9x11, filled with palette letter c."""
    rows = ["..XXXXX..", ".XXXXXXX.", ".XXXXXXX.", ".XXXXXXX.", ".XXXXXXX.", "..XXXXX..", ".........",
            "..XXXXX..", ".XXXXXXX.", "XXXXXXXXX", "XXXXXXXXX"]
    return [r.replace("X", c) for r in rows]


def slots(a, b, c):
    """One row of three 4x4 inventory slots (4 grid rows), colors by letter, light top-left pixel, dark bottom row."""
    shade = {"G": "g", "Y": "y", "B": "D"}
    out = []
    for i in range(4):
        cells = [("W" + k * 3) if i == 0 else (shade[k] * 4) if i == 3 else k * 4 for k in (a, b, c)]
        out.append("." + ".".join(cells) + ".")
    return out


ICONS = {
    # lobby hotbar: compass (slot 4)
    "game_selector": [layer([
        "................", "................", "................", "................",
        "..LLLLLLLLLLLL..",
        ".BBBBBBBBBBBBBB.",
        ".BBBKBBBBBBRRBB.",
        ".BBKKKBBBYYRRBB.",
        ".BBBKBBBBYYBBBB.",
        ".BBBBBBBBBBBBBB.",
        ".DDDDDDDDDDDDDD.",
        ".BBBB......BBBB.",
        ".BBB........BBB.",
        "..BB........BB..",
        "................", "................"])],
    # lobby hotbar: name tag (slot 0)
    "profile": [layer([
        "................", "................", "................",
        ".BBBBBBBBBBBBBB.",
        ".BBBBBBBBBBBBBB.",
        ".WWWWWWWWWWWWWW.",
        ".WWBBBBWWGGGGGW.",
        ".WWBBBBWWWWWWWW.",
        ".WWBBBBWWGGGGGW.",
        ".WWWBBWWWWWWWWW.",
        ".WBBBBBBWYYYWWW.",
        ".WBBBBBBWWWWWWW.",
        ".WWWWWWWWWWWWWW.",
        "................", "................", "................"])],
    # lobby hotbar: Twitch live list (slot 7)
    "live": [layer([
        "................", "................",
        ".PPPPPPPPPPPPPP.",
        ".PQQQQQQQQQQQQP.",
        ".PQQQQWQQQQRRQP.",
        ".PQQQQWWQQQRRQP.",
        ".PQQQQWWWQQQQQP.",
        ".PQQQQWWWQQQQQP.",
        ".PQQQQWWQQQQQQP.",
        ".PQQQQWQQQQQQQP.",
        ".PQQQQQQQQQQQQP.",
        ".PPPPPPPPPPPPPP.",
        ".......GG.......",
        ".....GGGGGGGG...",
        "................", "................"])],
    # profile menu "Einstellungen"; settings hotbar item of marathon, snake, bingo
    "settings": [layer([
        "........",
        "......BB",
        "..BB..BB",
        "..BBBBBB",
        "...BBBBB",
        "...BBBBB",
        ".BBBBBKK",
        ".BBBBBKK"], sym="quad")],
    # bridge: custom round comparator (slot 6) - a checklist with a pencil
    "custom_round": [layer([
        "......gggg......",
        "..WWWWggggWWWW..",
        "..WWWWWWWWWWWW..",
        "..WYYWGGGGGGWW..",
        "..WYYWWWWWWWWW..",
        "..WWWWWWWWWWWW..",
        "..WBBWGGGGGGWW..",
        "..WBBWWWWWWWWW..",
        "..WWWWWWWWWWWW..",
        "..WBBWGGGGWWWYY.",
        "..WBBWWWWWWWYYWW",
        "..WWWWWWWWWYYWW.",
        "..WWWWWWWWYYWWW.",
        "..WWWWWWWRRWWWW.",
        "................",
        "................"])],
    # bridge: hotbar layout chest (slot 4) - a hotbar strip with swap arrows
    "hotbar_layout": [layer([
        "................",
        "................",
        "KKKKKKKKKKKKKKKK",
        "KWGGGKWYYYKWBBBK",
        "KGGGGKYYYYKBBBBK",
        "KGGGGKYYYYKBBBBK",
        "KggggKyyyyKDDDDK",
        "KKKKKKKKKKKKKKKK",
        "................",
        "...........B....",
        "...BBBBBBBBBB...",
        "...........B....",
        ".....Y..........",
        "...YYYYYYYYYY...",
        ".....Y..........",
        "................"])],
    # profile menu "Cosmetics"
    "cosmetics": [layer([
        "................",
        "...B............",
        "..BBB.......L...",
        "...B.......LLL..",
        "......Y.....L...",
        "......Y.........",
        ".....YYY........",
        ".....YYY........",
        "..YYYYWYYYY.....",
        ".YYYYWWWYYYY....",
        "..YYYYWYYYY.....",
        ".....YYY.....B..",
        ".....YYY....BBB.",
        "......Y......B..",
        "......Y.........",
        "................"])],
    # profile menu "Freunde"
    "friends": [
        layer(bust("G"), dx=6, dy=1),
        layer(bust("B"), dx=1, dy=4),
    ],
    # profile menu "Bestwerte"
    "stats": [layer([
        "................", "................",
        "...........WW...",
        "...........YY...",
        "...........YY...",
        ".....LL....YY...",
        ".....BB....YY...",
        ".....BB.LL.YY...",
        "..LL.BB.BB.YY...",
        "..BB.BB.BB.YY...",
        "..BB.BB.BB.YY...",
        "..BB.BB.BB.YY...",
        "..BB.BB.BB.YY...",
        ".GGGGGGGGGGGGGG.",
        ".gggggggggggggg.",
        "................"])],
    # game selector start page: "Jeder gegen jeden"
    "category_ffa": [layer([
        "........",
        ".WG.....",
        "..WGg...",
        "...WGg..",
        "....WGg.",
        ".....WGg",
        "......WG",
        ".......W",
        ".....gGW",
        "..YYgGW.",
        "...YYW..",
        "....YY..",
        "...ggYY.",
        "..gg....",
        ".YY.....",
        "........"], sym="lr")],
    # "Teams"
    "category_teams": [layer([
        "................", "................",
        "..gRRRRR.gBBBBB.",
        "..gRRRRR.gBBBBB.",
        "..gRRRRR.gBBBBB.",
        "..gRRRRR.gBBBBB.",
        "..grrrrr.gDDDDD.",
        "..g......g......",
        "..g......g......",
        "..g......g......",
        "..g......g......",
        "..g......g......",
        "..g......g......",
        "..g......g......",
        ".ggg....ggg.....",
        "................"])],
    # "Solo"
    "category_solo": [layer([
        "................", "................",
        ".......BB.....Y.",
        "......BBBB...YYY",
        "......BBBB....Y.",
        ".......BB.......",
        "................",
        "....BBBBBBBB....",
        "...BBBBBBBBBB...",
        "...BB.BBBB.BB...",
        "...BB.BBBB.BB...",
        ".....BBBBBB.....",
        ".....BB..BB.....",
        ".....BB..BB.....",
        "....BBB..BBB....",
        "................"])],
    # "Kooperativ"
    "category_coop": [layer([
        "........",
        "........",
        "...BBBBB",
        "..BBBBBB",
        "..BBBBBY",
        "..BBBBBY",
        "..BBYYYY",
        "..BBYYYY",
        "..BBBBBY",
        "..BBBBBY",
        "...BBBBY",
        "....BBBY",
        ".....BBB",
        "......BB",
        ".......B",
        "........"], sym="lr")],
    # "Sonstige"
    "category_other": [layer([
        "................",
        "..BBBB....YYYY..",
        ".BBBBBB..YYYYYY.",
        ".BBBBBB..YYYYYY.",
        ".BBBBBB..YYYYYY.",
        ".BBBBBB..YYYYYY.",
        "..BBBB....YYYY..",
        "................", "................",
        "..GGGG....BBBB..",
        ".GGGGGG..BBBBBB.",
        ".GGGGGG..BBBBBB.",
        ".GGGGGG..BBBBBB.",
        ".GGGGGG..BBBBBB.",
        "..GGGG....BBBB..",
        "................"])],
}


def pixels(rows, sym):
    """{(x, y): (r, g, b, a)} of one layer, symmetry applied."""
    out = {}
    width, height = len(rows[0]), len(rows)
    for y, row in enumerate(rows):
        assert len(row) == width, f"row {y} is {len(row)} wide, expected {width}: {row!r}"
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            color = PALETTE[ch] + (255,)
            out[(x, y)] = color
            if sym in ("lr", "quad"):
                out[(2 * width - 1 - x, y)] = color
            if sym == "quad":
                out[(x, 2 * height - 1 - y)] = color
                out[(2 * width - 1 - x, 2 * height - 1 - y)] = color
    return out


def render(icon_id, layers):
    canvas = {}
    for rows, sym, dx, dy in layers:
        layer_px = {(x + dx, y + dy): c for (x, y), c in pixels(rows, sym).items()}
        for (x, y) in layer_px:
            assert 0 <= x < 16 and 0 <= y < 16, f"{icon_id}: pixel {(x, y)} outside 16x16"
        if sym is None and dx == 0 and dy == 0:
            assert len(rows) == 16 and len(rows[0]) == 16, f"{icon_id}: a full layer must be 16x16"
        outline = {(x + ox, y + oy) for (x, y) in layer_px for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1))}
        for p in outline:
            if p not in layer_px and 0 <= p[0] < 16 and 0 <= p[1] < 16:
                canvas[p] = PALETTE["K"] + (255,)
        canvas.update(layer_px)
    return canvas


def chunk(tag, data):
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def png(width, height, canvas):
    raw = b"".join(b"\x00" + b"".join(bytes(canvas.get((x, y), (0, 0, 0, 0))) for x in range(width)) for y in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8", newline="\n")  # no trailing newline, like team_choice*


def main():
    sheet = {}
    for n, (icon_id, layers) in enumerate(ICONS.items()):
        assert icon_id.islower() and icon_id.replace("_", "").isalnum(), f"bad id {icon_id}"
        assert not icon_id.startswith("team_choice"), "team_choice* is hand-made, not generated"
        canvas = render(icon_id, layers)
        texture = ASSETS / "textures" / "item" / f"{icon_id}.png"
        texture.parent.mkdir(parents=True, exist_ok=True)
        texture.write_bytes(png(16, 16, canvas))
        write_json(ASSETS / "models" / "item" / f"{icon_id}.json",
                   {"parent": "minecraft:item/generated", "textures": {"layer0": f"pandariamc:item/{icon_id}"}})
        write_json(ASSETS / "items" / f"{icon_id}.json",
                   {"model": {"type": "minecraft:model", "model": f"pandariamc:item/{icon_id}"}})
        for (x, y), c in canvas.items():  # contact sheet: 8 per row, 8x scale, 2px gap
            sheet[(x + (n % 8) * 18, y + (n // 8) * 18)] = c
    print(f"{len(ICONS)} icons written to {ASSETS}")
    if "--preview" in sys.argv:
        target = Path(sys.argv[sys.argv.index("--preview") + 1])
        w, h = 8 * 18, ((len(ICONS) + 7) // 8) * 18
        bg = (0x36, 0x39, 0x3F, 255)
        full = {}
        for y in range(h * 8):
            for x in range(w * 8):
                full[(x, y)] = sheet.get((x // 8, y // 8), bg)
        target.write_bytes(png(w * 8, h * 8, full))
        print(f"preview: {target}")


if __name__ == "__main__":
    main()
