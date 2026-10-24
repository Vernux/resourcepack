#!/usr/bin/env python3
"""Generates the item icons of the lobby's Cookie Clicker menu (stdlib only; PNG/JSON/outline helpers from make_item_icons.py).

Ids are `pandariamc:cookie/<name>` (nested like zeichnen/*), each as
  items/cookie/<name>.json + models/item/cookie/<name>.json (item/generated, layer0) + textures/item/cookie/<name>.png
Where each id is used: CookieIcons in paper/lobby (PandariaMc repo). Grids are at most 14x14 and centred on the 16x16 canvas;
render() adds the 1px outline. Re-run after editing a grid (idempotent). `--preview sheet.png` writes an 8x contact sheet
(8 per row, in ICONS order).
"""
import sys
from pathlib import Path

from make_item_icons import ASSETS, PALETTE, layer, png, render, write_json

# warm cookie / honey tones and a few helpers, letters for this script only
PALETTE.update({
    "c": (0xD9, 0xA0, 0x66), "C": (0xA8, 0x69, 0x2F),  # dough light / dark
    "d": (0x5A, 0x34, 0x18),                          # chocolate
    "o": (0xF0, 0x8A, 0x3C),                          # orange
    "e": (0x57, 0xF2, 0x87), "E": (0x2F, 0xA8, 0x54),  # success green light / dark
    "p": (0xF4, 0x9F, 0xC0),                          # pink
    "s": (0xE3, 0xC9, 0x8E), "S": (0xB0, 0x95, 0x5F),  # sand light / dark
    "h": (0xB0, 0x7A, 0x45), "H": (0x7E, 0x52, 0x2B),  # wood
    "f": (0xF2, 0xC9, 0x9B),                          # skin
    "m": (0x4A, 0x4D, 0x55),                          # iron dark
})


def disc(n, fill, shade, rim=None):
    """n x n round sprite: fill, shade on the lower right, rim (optional) on the edge."""
    def inside(x, y, shift=0, r=0.0):
        return (x + .5 - shift - n / 2) ** 2 + (y + .5 - shift - n / 2) ** 2 <= (n / 2 - r) ** 2
    return ["".join("." if not inside(x, y) else rim if rim and not inside(x, y, r=1) else shade if not inside(x, y, -1) else fill
                    for x in range(n)) for y in range(n)]


def put(rows, *pts):
    """rows with single pixels (x, y, letter) set."""
    grid = [list(r) for r in rows]
    for x, y, ch in pts:
        grid[y][x] = ch
    return ["".join(r) for r in grid]


def icon(rows):
    """One layer, centred on the 16x16 canvas."""
    return [layer(rows, dx=(16 - len(rows[0])) // 2, dy=(16 - len(rows)) // 2)]


CHIPS = [(4, 3), (5, 3), (9, 5), (4, 7), (5, 7), (8, 9), (9, 9), (6, 11), (11, 8), (7, 5)]
CURSOR = [
    "W.........", "WW........", "WGW.......", "WGGW......", "WGGGW.....", "WGGGGW....", "WGGGGGW...", "WGGGGWWW..",
    "WGWGW.....", "WW.WGW....", "W..WGW....", "....WGW...", "....WWW...",
]
RECOLOR_Y = str.maketrans("WG", "Yy")

ICONS = {
    "cookie/cookie": icon(put(disc(14, "c", "C"), *[(x, y, "d") for x, y in CHIPS])),
    "cookie/golden_cookie": icon(put(disc(14, "Y", "y", "y"), *[(x, y, "y") for x, y in CHIPS], (4, 4, "W"), (3, 5, "W"), (5, 4, "W"))),
    "cookie/prestige": icon([
        "......Y......", ".....YYY.....", ".....YWY.....", "....YYWYY....", "YYYYYWWWYYYYY", ".YYYYWWWYYYy.", "..YYYYWYYYy..",
        "...YYYWYYy...", "...YYYYYYy...", "..YYYyyyYYy..", "..YYy...yYy..", ".YYy.....yYy.", ".Yy.......yy."]),
    "cookie/click_upgrade": icon([r.translate(RECOLOR_Y) for r in CURSOR]),
    "cookie/locked": icon([
        "...GGGGGG...", "..Gg....gG..", "..Gg....gG..", "..Gg....gG..", ".YYYYYYYYYY.", ".YYYYYYYYYY.", ".YYYYKKYYYY.",
        ".YYYYKKYYYy.", ".YYYYYKYYYy.", ".YYYYYYYYYy.", ".yyyyyyyyyy."]),
    "cookie/check": icon(put(disc(14, "e", "E", "E"), (3, 7, "W"), (4, 7, "W"), (4, 8, "W"), (5, 8, "W"), (5, 9, "W"), (6, 9, "W"),
                             (6, 8, "W"), (7, 7, "W"), (7, 8, "W"), (8, 6, "W"), (8, 7, "W"), (9, 5, "W"), (9, 6, "W"), (10, 4, "W"),
                             (10, 5, "W"))),
    "cookie/hourglass": icon([
        "mmmmmmmmmm", "mWWWWWWWWm", ".WYYYYYYW.", "..WYYYYW..", "...WYYW...", "....WW....", "....WW....", "...W.YW...",
        "..W.YYYW..", ".W.YYYYYW.", "mWYYYYYYWm", "mmmmmmmmmm"]),
    "cookie/prestige_upgrade": icon([
        ".....YY.....", "....YYYY....", "...YYYYYY...", "..YYYyyYYY..", ".YYYy..yYYY.", "YYy......yYY", "............",
        "....YYYY....", "...YYYYYY...", "..YYYyyYYY..", ".YYYy..yYYY.", "YYy......yYY"]),
    "cookie/podium": icon([
        "....YYYYYy....", "....YYYYYy....", "GGGGYYYYYy....", "GGGGYYYYYy....", "GgggYYYYYycccc", "GgggYYYYYycCCc", "GgggYYYYYycCCc"]),
    # buildings
    "cookie/building_oma": icon([
        "....GGGG....", "...GGGGGG...", "..GGffffGG..", "..GfKffKfG..", "..GffffffG..", "...ffrrff...", "....ffff....",
        "..BBBBBBBB..", ".BBBBBBBBBB.", ".BBBBBBBBBB.", ".DDDDDDDDDD."]),
    "cookie/building_farm": icon([
        "..Y...Y...Y..", ".YYY.YYY.YYY.", ".YyY.YyY.YyY.", ".YYY.YYY.YYY.", ".YyY.YyY.YyY.", "..E...E...E..", "..E...E...E..",
        "cccccccccccCc", "CCCCCCCCCCCCC"]),
    "cookie/building_mine": icon([
        "..GGGGGGGG....", ".GGGGGGGGGG...", "GGg...hHGGG...", "Gg....hH.GG...", ".....hH...G...", "....hH........", "...hH.........",
        "..hH..........", ".hH...........", "hH............"]),
    "cookie/building_fabrik": icon([
        "..mm......mm..", "..mm......mm..", "..mm..GG..mm..", "..mm.G....mm..", "SSSSSSSSSSSSSS", "SGGSGGSGGSGGSS", "SGGSGGSGGSGGSS",
        "SSSSSSSSSSSSSS", "SYYSYYSYYSYYSS", "SYYSYYSYYSYYSS", "SSSSSSSSSSSSSS"]),
    "cookie/building_bank": icon([
        "......YY......", "....YYYYYY....", "..YYYYYYYYYY..", "YYYYYYYYYYYYYY", ".WG.WG.WG.WG..", ".WG.WG.WG.WG..", ".WG.WG.WG.WG..",
        ".WG.WG.WG.WG..", "yyyyyyyyyyyyyy", "yyyyyyyyyyyyyy"]),
    "cookie/building_tempel": icon([
        "......ss......", ".....ssss.....", "....ssssss....", "...ssssssss...", "..ssssssssss..", ".sssssKKsssss.", "ssssssKKssssSS",
        "ssssssKKssssSS", "SSSSSSSSSSSSSS"]),
    "cookie/building_zauberturm": icon([
        ".....Y.....", "....PPP....", "...PPPPP...", "..PPPYPPP..", ".PPPPPPPPP.", "QQQQQQQQQQQ", "...SGGGS...", "...SGYGS...",
        "...SGGGS...", "...SGGGS...", "...SGGGS...", "..SSSSSSS.."]),
    "cookie/building_portal": icon(put(disc(14, "Q", "Q", "P"), (3, 3, "L"), (4, 3, "B"), (3, 4, "B"), (9, 9, "B"), (10, 9, "L"),
                                       (6, 6, "B"), (7, 6, "L"), (6, 7, "L"), (7, 7, "B"), (5, 8, "B"), (8, 5, "B"), (10, 6, "B"),
                                       (3, 8, "B"))),
    "cookie/building_zeitmaschine": icon(put(disc(14, "W", "G", "B"), (6, 2, "K"), (6, 3, "K"), (6, 4, "K"), (6, 5, "K"), (6, 6, "K"),
                                             (7, 7, "K"), (6, 7, "K"), (7, 6, "K"), (8, 7, "K"), (9, 8, "K"))),
    "cookie/building_antimaterie": icon([
        "......B......", "......B......", "..B..LLL..B..", "...BLWWWLB...", "....LWWWL....", "BB.LWWWWWL.BB", "....LWWWL....",
        "...BLWWWLB...", "..B..LLL..B..", "......B......", "......B......"]),
    "cookie/building_hexenkessel": icon([
        "....e..e......", ".....ee..e....", "..gggggggggg..", "..eeeeeeeeee..", ".gggggggggggg.", ".gggggggggggg.", ".gggggggggggg.",
        "..gggggggggg..", "...gg....gg..."]),
    "cookie/building_wichtelwerkstatt": icon([
        "........WW..", ".......WWWW.", "......RRRRW.", ".....RRRRR..", "....RRRRRR..", "...RRRRRRR..", "..RRRRRRRR..", ".RRRRRRRRr..",
        "WWWWWWWWWW..", "WWWWWWWWWW.."]),
    "cookie/building_osterhasen": icon([
        "..WW....WW..", ".WppW..WppW.", ".WppW..WppW.", ".WppW..WppW.", ".WppWWWWppW.", "..WWWWWWWW..", ".WWWWWWWWWW.", ".WWKWWWWKWW.",
        ".WWWWppWWWW.", "..WWWWWWWW..", "...WWWWWW..."]),
    "cookie/building_eisdiele": icon([
        "...pppppp...", "..pppppppp..", ".pppWpppppp.", ".ppppppppWp.", ".WWWWWWWWWW.", "..oooooooo..", "..cooooooc..", "...cooooc...",
        "...ocococ...", "....ococ....", ".....coc....", "......c....."]),
    # tabs
    "cookie/tab_bakery": icon([
        "...cccccccc...", ".cccccccccccc.", "ccCcccCccccccc", "cccccccccccccC", "cccccccccccccC", ".CCCCCCCCCCCC."]),
    "cookie/tab_milestones": icon([
        "mmmmmmmmmmmmmm", "mmmmmmmmmmmmmm", "mmmmmmmmmmmmmm", ".mmmmmmmmmmm..", "...mmmmmmm....", "....mmmmmm....", "....mmmmmm....",
        "...mmmmmmmm...", "..mmmmmmmmmm..", "..mmmmmmmmmm.."]),
    "cookie/tab_prestige": icon([
        "...LLLLLL...", "..LLWBBBBD..", ".LWBBBBBBDD.", "LBBBBBBBBBDD", "BBBBBBBBBBDD", ".BBBBBBBBDD.", "..BBBBBBDD..", "...BBBBDD...",
        "....BBDD....", ".....DD....."]),
    "cookie/tab_research": icon([
        "...GGGG...", "...GWWG...", "....GG....", "....GG....", "...GGGG...", "..GGeeGG..", ".GGeeeeGG.", ".GeeeeeEG.", "GGeeeeeEEG",
        "GEEEEEEEEG", ".GGGGGGGG."]),
    "cookie/tab_skins": icon(put(disc(14, "c", "C"), *[(x, 3, "p") for x in range(3, 11)], *[(x, 4, "p") for x in range(3, 11)],
                                 (3, 5, "p"), (5, 5, "p"), (8, 5, "p"), (10, 5, "p"),
                                 (5, 4, "W"), (8, 3, "B"), (4, 4, "Y"), (9, 4, "L"), (6, 4, "e"),
                                 (4, 9, "d"), (8, 9, "d"), (6, 7, "d"), (9, 7, "d"))),
    "cookie/tab_achievements": icon([
        "YYYYYYYYYYYY", "YWYYYYYYYYYy", "YWYYYYYYYYYy", ".YYYYYYYYYYy", "..YYYYYYYYy.", "...YYYYYYy..", "....YYYYy...", ".....YYy....",
        ".....Yy.....", "....YYyy....", "...yyyyyy..."]),
    "cookie/tab_challenges": icon(put(disc(14, "W", "G", "R"), *[(x, y, "R") for x in (6, 7) for y in (3, 5, 6, 7, 8, 10)],
                                      *[(x, y, "R") for x in (3, 5, 8, 10) for y in (6, 7)])),
    "cookie/tab_stats": icon([
        "............", "........BB..", "........BL..", "...BB...BL..", "...BL...BL..", "...BL...BL..", "BB.BL.BBBL..", "BL.BL.BLBL..",
        "BL.BL.BLBL..", "BL.BL.BLBL..", "DDDDDDDDDDDD"]),
    # challenges
    "cookie/challenge_handarbeit": icon(CURSOR),
    "cookie/challenge_ohne_gold": icon(put(disc(14, "Y", "y", "y"), *[(i + 2, i + 2, "R") for i in range(10)],
                                           *[(i + 3, i + 2, "R") for i in range(10)])),
    "cookie/challenge_sprint": icon([
        "......YYYY..", ".....YYYY...", "....YYYY....", "...YYYYYYYY.", "..YYYYYYYY..", ".......YY...", "......YY....", ".....YY.....",
        "....Yy......", "...Yy.......", "..y........."]),
    "cookie/challenge_minimalist": icon([
        "....LLLL....", "..LLLLLLLL..", "LLLLLLLLLLLL", "BBBBBBBBBBBD", "BBBBBBBBBBBD", "BBBBBBBBBBBD", "BBBBBBBBBBBD",
        "BBBBBBBBBBBD", "BBBBBBBBBBBD", ".DDDDDDDDDD."]),
}


def main():
    sheet = {}
    for n, (icon_id, layers) in enumerate(ICONS.items()):
        assert icon_id.startswith("cookie/"), icon_id
        canvas = render(icon_id, layers)
        texture = ASSETS / "textures" / "item" / f"{icon_id}.png"
        texture.parent.mkdir(parents=True, exist_ok=True)
        texture.write_bytes(png(16, 16, canvas))
        write_json(ASSETS / "models" / "item" / f"{icon_id}.json",
                   {"parent": "minecraft:item/generated", "textures": {"layer0": f"pandariamc:item/{icon_id}"}})
        write_json(ASSETS / "items" / f"{icon_id}.json",
                   {"model": {"type": "minecraft:model", "model": f"pandariamc:item/{icon_id}"}})
        for (x, y), c in canvas.items():
            sheet[(x + (n % 8) * 18, y + (n // 8) * 18)] = c
    print(f"{len(ICONS)} icons written to {ASSETS}")
    if "--preview" in sys.argv:
        target = Path(sys.argv[sys.argv.index("--preview") + 1])
        w, h = 8 * 18, ((len(ICONS) + 7) // 8) * 18
        bg = (0x36, 0x39, 0x3F, 255)
        full = {(x, y): sheet.get((x // 8, y // 8), bg) for y in range(h * 8) for x in range(w * 8)}
        target.write_bytes(png(w * 8, h * 8, full))
        print(f"preview: {target}")


if __name__ == "__main__":
    main()
