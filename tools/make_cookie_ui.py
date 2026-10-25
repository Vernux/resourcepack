#!/usr/bin/env python3
"""Generates the font `pandariamc:cookie_ui` = the resource pack look of the lobby's Cookie Clicker menu (stdlib only;
PNG/JSON helpers from make_item_icons.py).

The plugin (paper:lobby `CookieMenuArt`, only while cookie.json `packUi` is on) writes the chest window's title as
  U+E023 (-8)  U+E000+page (background)  spaces  U+E010 (active tab)  spaces  <tab name in the default font>
Written here:
  pack/assets/pandariamc/font/cookie_ui.json
  pack/assets/pandariamc/textures/font/cookie_ui_<page>.png   176x222, one per tab (PAGES order = CookieMenu.Page order)
  pack/assets/pandariamc/textures/font/cookie_ui_tab.png      18x21, the highlight over the active tab's frame + a notch below it

Pixel layout (26.2 client, checked against ContainerScreen/AbstractContainerScreen/BitmapProvider and generic_54.png):
the 6-row chest window is 176x222, the title is drawn at window (8, 6), a bitmap glyph's top is at y + 7 - ascent, so the
backgrounds use ascent 13 (top = window y 0) and the highlight ascent -94 (top = window y 107 = frame of the bottom row).
A chest slot's item is at (8 + 18 * col, 18 + 18 * row), its 18x18 frame 1 px up/left; the player inventory frames start at
window y 138 (hotbar 196), the client draws "Inventar" at (8, 128) in 0x404040 on top of the art. The window outline follows
generic_54's shape exactly (same cut corners), so no vanilla pixel peeks out around the art. Items always render above the title.

Re-run after editing (idempotent). `--preview out.png` writes a 2x mock of all 8 tabs (4 per row): the art, the highlight on
that tab (all 8 tabs visible), grey squares where the plugin puts items, an accent bar where the tab name goes and a grey
bar for the client's "Inventar" label.
"""
import sys
from pathlib import Path

from make_item_icons import ASSETS, png, write_json

W, H = 176, 222
PAGES = ["bakery", "milestones", "prestige", "research", "skins", "achievements", "challenges", "stats"]
LABELS = ["Bäckerei", "Gebäude-Upgrades", "Prestige-Shop", "Forschung", "Keks-Sorten", "Erfolge", "Herausforderungen", "Statistiken"]

# Slots the plugin fills per tab (mirrors CookieMenu's slot constants; slot 4 header, 45-52 tabs and 53 close are on every tab).
BUILDINGS = list(range(19, 26)) + [30, 31, 32]
SEASONAL = [37, 39, 41, 43]
ITEMS = {
    "bakery": [11, 15] + BUILDINGS + SEASONAL,
    "milestones": [13] + BUILDINGS + SEASONAL,
    "prestige": [19, 21, 23, 25, 28, 30, 32, 34],
    "research": [10, 28, 11, 20, 29, 38, 21, 12, 13, 30, 31, 32, 33],
    "skins": list(range(19, 26)),
    "achievements": [s for row in (10, 19, 28, 37) for s in range(row, row + 7)],
    "challenges": [13, 19, 21, 23, 25, 28, 30, 32, 34],
    "stats": [22],
}
# Info/status items of a tab get the gold frame like the header.
GOLD = {"milestones": [13], "challenges": [13], "stats": [22]}
# Challenge top lists (a row below each challenge) get the cream "board" frame.
BOARD = {"challenges": [28, 30, 32, 34]}
# CookieResearch prerequisites (RESEARCH_SLOTS order): each route goes from slot to slot through the listed cells.
RESEARCH_ROUTES = [(10, 11), (10, 19, 20), (28, 19, 20), (28, 29), (28, 37, 38), (20, 21), (11, 12), (11, 12, 13),
                   (12, 13, 14, 15, 24, 33), (29, 30), (30, 31), (31, 32), (32, 33)]
INFO, TABS, CLOSE = 4, range(45, 53), 53

C = {  # cookie palette (same tones as make_cookie_icons.py)
    "out": (0x2B, 0x17, 0x0A), "cream": (0xF3, 0xDF, 0xB8), "cream_hi": (0xFF, 0xF4, 0xDC), "cream_lo": (0xC9, 0xA0, 0x6C), "cream_mid": (0xEA, 0xD0, 0xA2),
    "choc": (0x5A, 0x34, 0x18), "choc_dk": (0x3E, 0x22, 0x0E), "choc_hi": (0x7A, 0x4A, 0x24),
    "dough": (0xD9, 0xA0, 0x66), "dough_lo": (0xA8, 0x69, 0x2F), "dough_hi": (0xEC, 0xC2, 0x8C),
    "orange": (0xF0, 0x8A, 0x3C), "orange_hi": (0xFF, 0xC0, 0x78), "orange_dk": (0xB8, 0x5E, 0x1E),
}
STYLES = {  # slot frames: (top/left edge, bottom/right edge, inside)
    "slot": ((0x6B, 0x45, 0x22), C["cream_hi"], (0x9A, 0x68, 0x3A)),
    "gold": (C["orange_dk"], (0xFF, 0xE0, 0x8A), (0xD8, 0x8C, 0x38)),
    "board": (C["cream_lo"], C["cream_hi"], (0xE6, 0xCC, 0x9C)),
    "tab": (C["choc_dk"], C["dough_hi"], C["dough_lo"]),
    "close": ((0x6E, 0x1E, 0x1A), (0xF2, 0x9C, 0x8C), (0xA8, 0x3A, 0x32)),
    "player": ((0x8B, 0x6A, 0x48), C["cream_hi"], (0xC9, 0xA8, 0x80)),
}
# generic_54's transparent corner pixels: (left cut, right cut) per row (window rows 218-220 = texture rows 219-221).
CUTS = {0: (2, 3), 1: (1, 2), 2: (0, 1), 218: (1, 0), 219: (2, 1), 220: (3, 2), 221: (W, 0)}
CHIPS = [(9, 21), (21, 29), (33, 20), (46, 27), (58, 22), (102, 21), (114, 29), (127, 22), (139, 28), (152, 20), (164, 26)]


def inside(x, y):
    left, right = CUTS.get(y, (0, 0))
    return 0 <= y < H and left <= x < W - right


def slot_frame(slot):
    """Window position of a chest slot's 18x18 frame."""
    return 7 + 18 * (slot % 9), 17 + 18 * (slot // 9)


def rect(c, x0, y0, x1, y1, color):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            c[(x, y)] = color + (255,)


def frame(c, fx, fy, style):
    dark, light, fill = STYLES[style]
    rect(c, fx, fy, fx + 17, fy + 17, fill)
    rect(c, fx, fy, fx + 16, fy, dark)
    rect(c, fx, fy, fx, fy + 16, dark)
    rect(c, fx + 1, fy + 17, fx + 17, fy + 17, light)
    rect(c, fx + 17, fy + 1, fx + 17, fy + 17, light)
    rect(c, fx + 17, fy, fx + 17, fy, fill)  # the two mixed corners like vanilla
    rect(c, fx, fy + 17, fx, fy + 17, fill)


def cookie(c, cx, cy, r):
    """A small cookie disc with chocolate chips (header decoration)."""
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            d = (x - cx) ** 2 + (y - cy) ** 2
            if d <= r * r:
                c[(x, y)] = (C["out"] if d > (r - 1) ** 2 else C["dough_lo"] if x + y > cx + cy + r // 2 else C["dough"]) + (255,)
    for dx, dy in ((-2, -1), (1, -2), (2, 1), (-1, 2)):
        if abs(dx) < r and abs(dy) < r:
            c[(cx + dx, cy + dy)] = C["choc"] + (255,)


def link(c, a, b):
    """A 2 px orange line between the centres of two slot cells (orthogonal neighbours only)."""
    (ax, ay), (bx, by) = [(f[0] + 8, f[1] + 8) for f in (slot_frame(a), slot_frame(b))]
    rect(c, min(ax, bx), min(ay, by), max(ax, bx) + 1, max(ay, by) + 1, C["orange"])


def background(page):
    c = {}
    for y in range(H):
        for x in range(W):
            if inside(x, y):
                c[(x, y)] = C["cream"] + (255,)
    edge = {p for p in c if any(not inside(p[0] + dx, p[1] + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))}
    for p in c:
        x, y = p
        if p in edge:
            c[p] = C["out"] + (255,)
        elif (x - 1, y) in edge or (x, y - 1) in edge:
            c[p] = C["cream_hi"] + (255,)
        elif (x + 1, y) in edge or (x, y + 1) in edge:
            c[p] = C["cream_lo"] + (255,)
    # title strip (the tab name is written at y 6-13) with a cookie on the right
    rect(c, 4, 3, 171, 15, C["choc"])
    rect(c, 4, 3, 171, 3, C["choc_hi"])
    rect(c, 4, 15, 171, 15, C["choc_dk"])
    cookie(c, 164, 9, 5)
    # header row (row 0): a dough band with chips, the balance item (slot 4) in a gold frame with an orange glow
    rect(c, 4, 17, 171, 34, C["dough"])
    rect(c, 4, 17, 171, 17, C["dough_hi"])
    rect(c, 4, 34, 171, 34, C["dough_lo"])
    for x, y in CHIPS:
        rect(c, x, y, x + 1, y + 1, C["choc"])
    fx, fy = slot_frame(INFO)
    rect(c, fx - 2, fy, fx + 19, fy + 17, C["orange"])
    frame(c, fx, fy, "gold")
    # rows 1-4: a slightly recessed panel, then the tab's own slot frames
    rect(c, 4, 35, 171, 106, C["cream_mid"])
    rect(c, 4, 35, 171, 35, C["cream_lo"])
    for slot in ITEMS[page]:
        style = "gold" if slot in GOLD.get(page, []) else "board" if slot in BOARD.get(page, []) else "slot"
        frame(c, *slot_frame(slot), style)
    if page == "research":
        for route in RESEARCH_ROUTES:
            for a, b in zip(route, route[1:]):
                link(c, a, b)
        for slot in ITEMS[page]:  # the line stays on the frames and in empty cells, never under an item
            fx, fy = slot_frame(slot)
            rect(c, fx + 1, fy + 1, fx + 16, fy + 16, STYLES["slot"][2])
    # tab bar (slots 45-52) + close (53) on a chocolate strip
    rect(c, 4, 107, 171, 125, C["choc"])
    rect(c, 4, 125, 171, 125, C["choc_dk"])
    for slot in TABS:
        frame(c, *slot_frame(slot), "tab")
    frame(c, *slot_frame(CLOSE), "close")
    # player inventory (3 rows from y 138) + hotbar (y 196) in light frames; "Inventar" (8, 128) stays on cream
    for row in range(3):
        for col in range(9):
            frame(c, 7 + 18 * col, 138 + 18 * row, "player")
    for col in range(9):
        frame(c, 7 + 18 * col, 196, "player")
    return c


def highlight():
    """The active tab: a glowing 18x18 frame (window y 107-124) and a notch under it on the bar's lower edge (y 125-127)."""
    c = {}
    rect(c, 0, 0, 17, 17, C["orange_hi"])
    rect(c, 1, 1, 16, 16, C["orange"])
    rect(c, 2, 2, 15, 15, (0xFF, 0xB0, 0x5E))
    rect(c, 5, 18, 12, 18, C["orange"])
    rect(c, 6, 19, 11, 19, C["orange"])
    rect(c, 7, 20, 10, 20, C["orange_dk"])
    return c


def preview(target, backgrounds, tab):
    cols, scale, gap = 4, 2, 8
    cw, ch = W * scale + gap, H * scale + gap
    sheet_w, sheet_h = cols * cw + gap, ((len(PAGES) + cols - 1) // cols) * ch + gap
    bg = (0x36, 0x39, 0x3F, 255)
    sheet = {}
    for n, page in enumerate(PAGES):
        c = dict(backgrounds[page])
        fx, fy = slot_frame(45 + n)
        for (x, y), v in tab.items():
            c[(fx + x, fy + y)] = v
        for slot in ITEMS[page] + [INFO] + list(TABS) + [CLOSE]:
            ix, iy = slot_frame(slot)
            rect(c, ix + 1, iy + 1, ix + 16, iy + 16, (0x80, 0x80, 0x80))
        rect(c, 8, 7, 8 + 6 * len(LABELS[n]) - 2, 12, (0xFE, 0xE7, 0x5C))  # tab name, ~6 px per default-font char
        rect(c, 8, 129, 8 + 6 * len("Inventar") - 2, 134, (0x40, 0x40, 0x40))
        ox, oy = gap + (n % cols) * cw, gap + (n // cols) * ch
        for (x, y), v in c.items():
            for sy in range(scale):
                for sx in range(scale):
                    sheet[(ox + x * scale + sx, oy + y * scale + sy)] = v
    full = {(x, y): sheet.get((x, y), bg) for y in range(sheet_h) for x in range(sheet_w)}
    target.write_bytes(png(sheet_w, sheet_h, full))
    print(f"preview: {target}")


def main():
    textures = ASSETS / "textures" / "font"
    textures.mkdir(parents=True, exist_ok=True)
    backgrounds = {page: background(page) for page in PAGES}
    providers = [{"type": "space", "advances": {chr(0xE020 + bit): -(1 << bit) for bit in range(9)}}]
    for n, page in enumerate(PAGES):
        assert max(x for x, _ in backgrounds[page]) == W - 1  # glyph width 176 -> advance 177 (CookieMenuArt)
        (textures / f"cookie_ui_{page}.png").write_bytes(png(W, H, backgrounds[page]))
        providers.append({"type": "bitmap", "file": f"pandariamc:font/cookie_ui_{page}.png", "ascent": 13, "height": H,
                          "chars": [chr(0xE000 + n)]})
    tab = highlight()
    assert max(x for x, _ in tab) == 17  # glyph width 18 -> advance 19 (CookieMenuArt)
    (textures / "cookie_ui_tab.png").write_bytes(png(18, 21, tab))
    providers.append({"type": "bitmap", "file": "pandariamc:font/cookie_ui_tab.png", "ascent": -94, "height": 21, "chars": [chr(0xE010)]})
    write_json(ASSETS / "font" / "cookie_ui.json", {"providers": providers})
    print(f"{len(PAGES)} backgrounds + tab highlight written to {ASSETS}")
    if "--preview" in sys.argv:
        preview(Path(sys.argv[sys.argv.index("--preview") + 1]), backgrounds, tab)


if __name__ == "__main__":
    main()
