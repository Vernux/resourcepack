#!/usr/bin/env python3
"""Generates the 16x16 item icons of the PandariaMc server pack (stdlib only).

For every id in ICONS it writes
  pack/assets/pandariamc/textures/item/<id>.png   16x16 RGBA
  pack/assets/pandariamc/models/item/<id>.json    item/generated + layer0
  pack/assets/pandariamc/items/<id>.json          item definition (what `ItemBuilder#model(id)` selects)

The team_choice* icons are NOT made here (hand-made, left alone). The plugin side (id -> item): "Custom item
models" in the PandariaMc repo's CLAUDE.md. Re-run after editing a grid; `--preview sheet.png` also writes an 8x
contact sheet of all icons to look at.

Grids are rows of chars, letters = the layer's palette, '.' = transparent. sym="lr": rows hold the left 8 columns,
mirrored; sym="quad": the top-left 8x8, mirrored both ways. A multi-layer icon stamps its layers in order (each one
outlined, so a later layer is separated from an earlier one).

Outline (added by render, only onto transparent pixels, 4-neighbour, so leave a 1px border free):
  "K"   one letter = a uniform outline in that color (the old flat look, still used by make_cookie_icons.py)
  "ko"  two letters = the vanilla look: k on the top/left side of the shape, o on the bottom/right side
        (light from the top-left, like Mojang's items); a hole inside the shape gets the inverse bevel for free
  None  no outline (hand-drawn in the grid, or thin details like string)
The menu icons are drawn like vanilla items: MATERIALS ramps (dark, mid, light, highlight), highlights top-left,
shadow bottom-right, a warm dark outline instead of black. mat("okdmlh", "iron") maps letters onto a material.
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

# vanilla-style material ramps: outline bottom/right, outline top/left, dark, mid, light, highlight
MATERIALS = {
    "iron":     (0x1F1E22, 0x46474D, 0x5B5C63, 0x8E9097, 0xC3C5CA, 0xEEEFF1),
    "gold":     (0x3F2606, 0x7A4E10, 0xA66B17, 0xD9A228, 0xF5D04A, 0xFFF3A6),
    "wood":     (0x241607, 0x3E2910, 0x5A3C1A, 0x7F5A2B, 0xA47A40, 0xC99C5C),
    "plank":    (0x2A1A08, 0x4A3115, 0x6B4720, 0x936530, 0xB98745, 0xD6A65E),
    "leather":  (0x26140A, 0x45250F, 0x5A3215, 0x7C4A22, 0xA16A38, 0xC58A52),
    "paper":    (0x3E3220, 0x7A6A4A, 0xB6A682, 0xD9CCAA, 0xEFE6CC, 0xFFFBEE),
    "string":   (0x2E2E30, 0x5A5A5E, 0x8C8C8C, 0xB9B9B9, 0xDDDDDD, 0xF6F6F6),
    "redstone": (0x2A0404, 0x4A0808, 0x6E0E0E, 0xA81616, 0xE02424, 0xFF7A6A),
    "amethyst": (0x22123E, 0x3A2266, 0x55358F, 0x7A55BF, 0xA88AE6, 0xE2D6FF),
    "diamond":  (0x141C40, 0x26326E, 0x34449A, 0x4B5DA9, 0x7289DA, 0xC6D2FA),  # network blue as a gem
    "emerald":  (0x062A14, 0x0B4A24, 0x137A3A, 0x23A852, 0x57F287, 0xCDFFDE),  # network green as a gem
    "twitch":   (0x1A0A3A, 0x2E1466, 0x4A22A0, 0x6A30D6, 0x9146FF, 0xD2B8FF),  # Twitch purple glass
    "red":      (0x2C0808, 0x4E1214, 0x7A1C1F, 0xA82E31, 0xED4245, 0xFF8E8E),  # cloth, network red
    "blue":     (0x10173A, 0x222D66, 0x34428A, 0x4B5DA9, 0x7289DA, 0xAFC0F5),  # cloth, network blue
    "yellow":   (0x3A2C04, 0x6E5408, 0x9C7A12, 0xC9A82A, 0xFEE75C, 0xFFF7C2),  # cloth, network yellow
    "skin":     (0x2A160C, 0x5A3420, 0xB57A55, 0xD29A70, 0xE8B88E, 0xF7D3AE),
    "skin_dark": (0x1C0E06, 0x3E2414, 0x6A4228, 0x8A5A38, 0xA8744C, 0xC08C62),
    "hair":     (0x1E1209, 0x2E1C0E, 0x3E2612, 0x5A3818, 0x744A22, 0x8E5E2E),
    "hair_dark": (0x0C0806, 0x16100C, 0x1E1612, 0x2E241C, 0x3E3226, 0x52443A),
}


def rgb(v):
    return (v >> 16) & 255, (v >> 8) & 255, v & 255


def mat(letters, material):
    """{letter: color} for up to 6 letters onto MATERIALS[material] (outline dark, outline light, dark, mid, light,
    highlight); '_' skips a step, e.g. mat("o_dmlh", "iron")."""
    return {ch: rgb(c) for ch, c in zip(letters, MATERIALS[material]) if ch != "_"}


def colors(**hexes):
    """{letter: color} from single-letter keyword args, e.g. colors(w=0xFFFFFF)."""
    return {ch: rgb(c) for ch, c in hexes.items()}


def layer(rows, sym=None, dx=0, dy=0, outline="K", palette=None):
    return rows, sym, dx, dy, outline, palette or PALETTE


FACE_A = [  # 8x8 player face: brown hair, light skin, blue eyes
    "llllllld",
    "lldllldd",
    "dSsssssd",
    "Ssssssss",
    "swbssbws",
    "sssmmsss",
    "ssnnnnsm",
    "mmmmmmmm",
]
FACE_B = [  # 8x8 player face: black hair, darker skin, green eyes, longer fringe
    "lllllldd",
    "ldlllddd",
    "dldSsdld",
    "Ssssssss",
    "swessews",
    "sssmmsss",
    "ssnnnnsm",
    "mmmmmmmm",
]

SWORD = [  # tip top-right, hilt bottom-left; mirrored for the second sword of category_ffa
    "................",
    ".............hl.",
    "............hl..",
    "...........hl...",
    "..........hl....",
    ".........hl.....",
    "........hl......",
    "...ss..hl.......",
    "....ss.l........",
    ".....sl.........",
    "....wWs.........",
    "...wW..ss.......",
    "..wW............",
    ".ii.............",
    ".i..............",
    "................",
]
SWORD_PAL = mat("okdmlh", "iron") | mat("___sS", "iron") | mat("___Ww", "wood") | mat("____i", "gold")

BANNER = [  # 7 wide: crossbar, cloth (letters c/C/D/E = light, mid, dark, darkest), white stripe, pole
    "hwwwwww",
    ".cCCCD.",
    ".cCCCD.",
    ".vvvvV.",
    ".VVVVV.",
    ".cCCCD.",
    ".cCCCD.",
    ".cCCCD.",
    ".CCCDD.",
    ".DDDDE.",
    "...w...",
    "...w...",
]


def banner(material):
    return mat("ok__wh", "wood") | mat("__EDCc", material) | colors(v=0xF2EEEA, V=0xC4BCB6)


ICONS = {
    # lobby hotbar: compass (slot 4) - iron rim, blue glass face, red/white needle
    "game_selector": [layer([
        "................",
        "................",
        "......hhll......",
        "....hhllllmm....",
        "...hllFFffmmd...",
        "...llFfffffrd...",
        "..llFffffrRfmd..",
        "..lmffffrRffmd..",
        "..mmfffwWfffdd..",
        "..mdffwWffffdd..",
        "...mdwWffffdd...",
        "...dddffffddd...",
        "....dddddddd....",
        "......dddd......",
        "................",
        "................"], outline="ko",
        palette=mat("okdmlh", "iron") | mat("__F", "blue") | colors(f=0x222C5E) | mat("___Rr", "red") | colors(w=0xF6F6F6, W=0xB8B9BE))],
    # lobby hotbar: name tag (slot 0) - paper tag, blue header band, string loop through the hole
    "profile": [
        layer([
            "................",
            "................",
            "................",
            "................",
            "................",
            "................",
            "....hllllllllm..",
            "...hlBBBBBBBBm..",
            "..hllDDDDDDDDm..",
            "..l.lllllllllm..",
            "..llltttlttttd..",
            "...mlllllllldd..",
            "....mmmmmmmmmd..",
            "................",
            "................",
            "................"], outline="ko",
            palette=mat("okdmlh", "paper") | mat("___DB", "blue") | colors(t=0x8A7450)),
        layer([
            "................",
            "................",
            "...sss..........",
            "..s...S.........",
            "..s...S.........",
            "..s...S.........",
            "...SSS..........",
            "...S............",
            "...S............",
            "................",
            "................",
            "................",
            "................",
            "................",
            "................",
            "................"], outline=None, palette=colors(s=0xE6E6E6, S=0x5E5E62)),
    ],
    # lobby hotbar: Twitch live list (slot 7) - an old wooden TV, purple glass screen, redstone "on air" lamp
    "live": [
        layer([
            "................",
            "....a......a....",
            ".....a....a.....",
            "......a..a......",
            ".......aa.......",
            "................",
            "................",
            "................",
            "................",
            "................",
            "................",
            "................",
            "................",
            "................",
            "................",
            "................"], outline=None, palette=mat("__a", "iron")),
        layer([
            "................",
            "................",
            "................",
            "................",
            "................",
            "................",
            "..hhhhhhhhhhhl..",
            "..hGGPPPPPPlhm..",
            "..hGPPPPPPpXRm..",
            "..lPPPPPPPpRrm..",
            "..lPPPPPPppllm..",
            "..lPPPPPppqdmm..",
            "..lppppppqqdmm..",
            "..mmmmmmmmmmmd..",
            "...d........d...",
            "................"], outline="ko",
            palette=mat("okdmlh", "wood") | mat("__qpP", "twitch") | mat("____RX", "red") | colors(G=0xE4D6FF, r=0xA82E31)),
    ],
    # profile menu "Einstellungen"; settings hotbar item of marathon, snake, bingo - an iron cog
    "settings": [layer([
        "................",
        "................",
        "......hlll......",
        "...hl.lllm.lm...",
        "...lllhlllmmd...",
        "....lhllmmmd....",
        "..hlllm..mmmmd..",
        "..lllm....mmdd..",
        "..lmmm....mddd..",
        "..mmmmm..ddddd..",
        "....mmmmdddd....",
        "...mmmmdddddd...",
        "...mm.mddd.dd...",
        "......dddd......",
        "................",
        "................"], outline="ko", palette=mat("okdmlh", "iron"))],
    # bridge: custom round comparator (slot 6) - book and quill: leather book, blue bookmark, feather
    "custom_round": [
        layer([
            "................",
            "................",
            "................",
            "................",
            "..dlhhhhhhl.....",
            "..dlllllllmp....",
            "..dlllllllmp....",
            "..dllpppplmp....",
            "..dllPPPPlmp....",
            "..dllllmllmp....",
            "..dlmllllmmp....",
            "..dmmmmmmmmp....",
            "..dmmmmmmmdp....",
            "...pBppppppP....",
            "....D...........",
            "................"], outline="ko",
            palette=mat("okdmlh", "leather") | mat("___Pp", "paper") | mat("___DB", "blue")),
        layer([
            "................",
            ".............ww.",
            "............wwW.",
            "...........wWg..",
            "..........wWg...",
            ".........wWg....",
            "........wWg.....",
            "........Wg......",
            ".......q........",
            "......n.........",
            "................",
            "................",
            "................",
            "................",
            "................",
            "................"], outline="ko",
            palette=mat("ok_gWw", "string") | colors(q=0x8C8C8C, n=0x26262A)),
    ],
    # bridge: hotbar layout chest (slot 4) - oak chest with an iron latch
    "hotbar_layout": [layer([
        "................",
        "................",
        ".hhhhhhhhhhhhhl.",
        ".hlllllllllllmd.",
        ".llmlllllllmlmd.",
        ".lllllllllllmmd.",
        ".mmmmmmiimmmmmd.",
        ".kkkkkkiIkkkkkk.",
        ".hllllkIIkllmmd.",
        ".llllllllllllmd.",
        ".llmllllllllmmd.",
        ".lllllllllmlmmd.",
        ".mmmmmmmmmmmmmd.",
        ".dddddddddddddd.",
        "................",
        "................"], outline="ko",
        palette=mat("o_dmlh", "plank") | mat("_k", "plank") | mat("___Ii", "iron"))],
    # profile menu "Cosmetics" - a gem cluster: diamond-blue, amethyst, emerald-green crystal, a sparkle
    "cosmetics": [
        layer([
            "................",
            "................",
            "................",
            "................",
            "................",
            "..hl............",
            ".hllm...........",
            ".hlmd...........",
            ".hlmd...........",
            ".llmd...........",
            ".llmd...........",
            ".lmmd...........",
            ".mmdd...........",
            "................",
            "................",
            "................"], outline="ko", palette=mat("okdmlh", "diamond")),
        layer([
            "................",
            "................",
            "................",
            "................",
            "................",
            "................",
            "................",
            "............hl..",
            "...........hlmd.",
            "...........hlmd.",
            "...........llmd.",
            "...........lmmd.",
            "...........mmdd.",
            "................",
            "................",
            "................"], outline="ko", palette=mat("okdmlh", "emerald")),
        layer([
            "................",
            ".......hl.......",
            "......hhlm......",
            "......hlmd......",
            "......hlmd......",
            "......hlmd......",
            "......llmd......",
            "......llmd......",
            "......lmmd......",
            "......lmmd......",
            "......lmdd......",
            "......mmdd......",
            "......mddd......",
            "................",
            "................",
            "................"], outline="ko", palette=mat("okdmlh", "amethyst")),
        layer([
            "................",
            ".............y..",
            "............yYy.",
            ".............y..",
            "................",
            "................",
            "................",
            "................",
            "................",
            "................",
            "................",
            "................",
            "................",
            "................",
            "................",
            "................"], outline=None, palette=mat("____yY", "yellow")),
    ],
    # profile menu "Freunde" - two player heads
    "friends": [
        layer(FACE_A, dx=7, dy=1, outline="ko",
              palette=mat("ok_dl", "hair") | mat("__mSs", "skin") | colors(w=0xF4F4F4, b=0x4B5DA9, n=0x8A4A3A)),
        layer(FACE_B, dx=1, dy=6, outline="ko",
              palette=mat("ok_dl", "hair_dark") | mat("__mSs", "skin_dark") | colors(w=0xF4F4F4, e=0x23A852, n=0x4A2A1E)),
    ],
    # profile menu "Bestwerte" - a parchment map with a rising bar chart
    "stats": [layer([
        "................",
        "................",
        "..lllllllllllm..",
        "..lhhhhhhhhhhm..",
        "..lhhhhhhhBDhd..",
        "..lhhhhhhhBDhd..",
        "..lhhhhYyhBDhm..",
        "..mhhhhYyhBDhd..",
        "..lhGghYyhBDhd..",
        "..lhGghYyhBDhm..",
        "..lhGghYyhBDhd..",
        "..lhGghYyhBDhd..",
        "..mddddddddddd..",
        "..mmlmmmmlmmmd..",
        "................",
        "................"], outline="ko",
        palette=mat("okdmlh", "paper") | mat("___yY", "yellow") | mat("___DB", "blue") | mat("___gG", "emerald"))],
    # game selector start page: "Jeder gegen jeden" - two crossed iron swords
    "category_ffa": [
        layer([r[::-1] for r in SWORD], outline="ko", palette=SWORD_PAL),
        layer(SWORD, outline="ko", palette=SWORD_PAL),
    ],
    # "Teams" - a red and a blue banner
    "category_teams": [
        layer(BANNER, dx=1, dy=1, outline="ko", palette=banner("red")),
        layer(BANNER, dx=8, dy=2, outline="ko", palette=banner("blue")),
    ],
    # "Solo" - one player head, big
    "category_solo": [layer([
        "................",
        "................",
        "..AAAAAAAAAAAa..",
        "..AAaAAAAaAAaa..",
        "..aAaaAAaaAaaa..",
        "..aLsssssssSSa..",
        "..Lsssssssssss..",
        "..LswbbssbbwsS..",
        "..LswBBssBBwsS..",
        "..LssssSSssssS..",
        "..LsssmmmmsssS..",
        "..ssssssssssSS..",
        "..SSSSSSSSSSSS..",
        "................",
        "................",
        "................"], outline="ko",
        palette=mat("ok_aA", "hair") | mat("__SsL", "skin") | colors(w=0xF4F4F4, b=0x7289DA, B=0x4B5DA9, m=0x8A4A3A))],
    # "Kooperativ" - a shield with an iron rim and boss, field split blue | yellow
    "category_coop": [layer([
        "................",
        "..hhhhhhhhhhhm..",
        "..hLBBBBYYYYyd..",
        "..hLBBBBYYYYyd..",
        "..hLBBBBYYYYyd..",
        "..lBBBBBYYYYyd..",
        "..lBBBBBYYYyyd..",
        "..lBBBBBYYYyyd..",
        "..lBBBBBYYYyyd..",
        "..lDBBBBYYyyyd..",
        "...lDBBBYYyyd...",
        "....lDDDyyyd....",
        ".....mDDyyd.....",
        "......mddd......",
        "................",
        "................"], outline="ko",
        palette=mat("okdmlh", "iron") | mat("___DBL", "blue") | mat("___yY", "yellow"))],
    # "Sonstige" - a leather bundle tied with string
    "category_other": [layer([
        "................",
        ".....hl..lm.....",
        ".....hlllmm.....",
        "......lllm......",
        ".....sssssS.....",
        "....hllllllm....",
        "...hllllllmmd...",
        "..hhllllllmmmd..",
        "..hlllllllmmmd..",
        "..lllmlllllmmd..",
        "..llllllmmmmdd..",
        "..lmllmmmmmmdd..",
        "..mmmmmmmmmddd..",
        "...mmmmmmdddd...",
        "....dddddddd....",
        "................"], outline="ko",
        palette=mat("okdmlh", "leather") | mat("___Ss", "string"))],
}


def pixels(rows, sym, palette):
    """{(x, y): (r, g, b, a)} of one layer, symmetry applied."""
    out = {}
    width, height = len(rows[0]), len(rows)
    for y, row in enumerate(rows):
        assert len(row) == width, f"row {y} is {len(row)} wide, expected {width}: {row!r}"
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            color = palette[ch] + (255,)
            out[(x, y)] = color
            if sym in ("lr", "quad"):
                out[(2 * width - 1 - x, y)] = color
            if sym == "quad":
                out[(x, 2 * height - 1 - y)] = color
                out[(2 * width - 1 - x, 2 * height - 1 - y)] = color
    return out


def render(icon_id, layers):
    canvas = {}
    for rows, sym, dx, dy, outline, palette in layers:
        layer_px = {(x + dx, y + dy): c for (x, y), c in pixels(rows, sym, palette).items()}
        for (x, y) in layer_px:
            assert 0 <= x < 16 and 0 <= y < 16, f"{icon_id}: pixel {(x, y)} outside 16x16"
        if sym is None and dx == 0 and dy == 0:
            assert len(rows) == 16 and len(rows[0]) == 16, f"{icon_id}: a full layer must be 16x16"
        if outline:
            light, dark = palette[outline[0]], palette[outline[-1]]
            for (x, y) in {(x + ox, y + oy) for (x, y) in layer_px for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1))}:
                if (x, y) in layer_px or not (0 <= x < 16 and 0 <= y < 16):
                    continue
                # shape above or left of this pixel = it sits on the bottom/right side = the dark outline
                canvas[(x, y)] = (dark if (x - 1, y) in layer_px or (x, y - 1) in layer_px else light) + (255,)
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
