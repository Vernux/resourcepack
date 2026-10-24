#!/usr/bin/env python3
"""Generates the PandariaMC trailer: a ~13.5 s pixel-art animation as ONE animated item texture (numpy + stdlib; PNG/JSON helpers from make_item_icons.py).

Needs numpy (`pip install numpy`), nothing else. Run it as `python tools/make_trailer.py` (NOT `python -I`: that would hide numpy),
`--preview sheet.png` also writes a contact sheet (every 9th frame, 1x) to look at. Takes ~30 s; running it twice writes the same bytes.

All under pack/assets/pandariamc/, the id is `pandariamc:trailer`:
  items/trailer.json + models/item/trailer.json (item/generated, layer0)
  textures/item/trailer.png          ONE vertical strip, 320 x (frames * 180), frames top to bottom, indexed 8-bit PNG (color type 3, one global
                                     256-color median-cut palette over all frames, row filter none)
  textures/item/trailer.png.mcmeta   {"animation": {"frametime": 2, "width": 320, "height": 180}}: the client plays it itself (10 fps), no server load

How the plugin shows it (paper:lobby streamwall.*, `/streamwall trailer`): an ItemDisplay on a PAPER stack with the item model `pandariamc:trailer`,
display transformation FIXED. The generated model is a flat square of 1 block - whatever the texture's aspect ratio - so the plugin scales it
to the 16:9 rectangle it wants (width x width * 9/16 blocks). That is why the frame is 16:9. The plugin side: paper/lobby/CLAUDE.md in the
PandariaMc repo.

Content: four scenes (title, the minigame list, the Zeichnen panda, the outro with the menu icons), drawn pixel by pixel with numpy.
Texts and scene lengths are the constants below; the 5x7 font has only A-Z 0-9 . , ! ? : - + / ' * and space (no umlauts, other characters
show as ?). The outro and the Zeichnen scene read icons from textures/item/ (game_selector, friends, cosmetics, stats, live, zeichnen/brush
+ brush_paint): re-run after those change.

Pack build: 320 x 24300 is taller than PackSquash's default `maximum_width_and_height` (8192) - the release workflow raises it for this one file
(.github/workflows/build.yml). Client: 180 is divisible by 4 only, so the client logs "limits mip level from 4 to 2" for this texture (harmless).
"""
import math
import sys
import zlib
from pathlib import Path

import numpy as np

from make_item_icons import ASSETS, chunk, write_json

# ---------------------------------------------------------------- timing + texts (change here)
W, H = 320, 180  # one frame, 16:9
SOURCE_FPS = 12  # SCENES below count frames at this rate
FRAMETIME = 2  # game ticks per frame in the .mcmeta: 2 = 10 fps
OUT_FPS = 20 // FRAMETIME
SCENES = [("title", 30), ("games", 44), ("draw", 48), ("outro", 40)]  # (scene, length in SOURCE_FPS frames)
WIPE = 5  # frames of the wipe between two scenes

TITLE = "PANDARIAMC"
SUBTITLE = "DEIN MINISPIEL-NETZWERK"
GAMES_HEADING = "MINISPIELE"
GAMES = ["SUMO", "BRIDGE", "BLOCKPARTY", "COLORMATCH", "TNTRUN", "SPLEEF", "SNAKE", "ELYTRON", "ELYTRARACE",
         "MARATHON", "BINGO", "CUBEBALL", "CUBEHOCKEY", "BILLARD", "CURLING", "GOLF", "BOWLING", "SPLASH",
         "FROGGER", "TOWERDEFENSE", "KETTENREAKTION", "JENGA", "RHYTHMUSLAUF", "WETTANGELN", "ZEICHNEN",
         "TASTENTAKT", "ZIELSCHMETTERN"]
DRAW_HEADING = "ZEICHNEN UND RATEN"
DRAW_HINT = "ZEICHNE - DIE ANDEREN RATEN IM CHAT"
CHAT_HEADING = "CHAT"
CHAT_LINES = [(22, "ANNA", "HUND?", False), (28, "BEN", "BAER?", False), (34, "CARLO", "PANDA!", True)]  # (frame, who, message, correct)
CORRECT = "RICHTIG!"
POINTS = "+10 PUNKTE"
OUTRO_HEADING = "UND ALLES DRUMHERUM"
FEATURES = [("game_selector.png", "SPIELE"), ("friends.png", "FREUNDE"), ("cosmetics.png", "COSMETICS"),
            ("stats.png", "RANGLISTE"), ("live.png", "LIVE")]  # (icon in textures/item/, label)
TAGLINE = "MINISPIELE - FREUNDE - SPASS"

# the network palette (api:text Colors) + backgrounds
BG2 = (43, 45, 49)
PRIMARY = (114, 137, 218)
SECOND = (181, 186, 193)
ACCENT = (254, 231, 92)
GREEN = (87, 242, 135)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# ---------------------------------------------------------------- font 5x7
_G = {
    "A": ".###.|#...#|#...#|#####|#...#|#...#|#...#",
    "B": "####.|#...#|#...#|####.|#...#|#...#|####.",
    "C": ".####|#....|#....|#....|#....|#....|.####",
    "D": "####.|#...#|#...#|#...#|#...#|#...#|####.",
    "E": "#####|#....|#....|####.|#....|#....|#####",
    "F": "#####|#....|#....|####.|#....|#....|#....",
    "G": ".####|#....|#....|#.###|#...#|#...#|.###.",
    "H": "#...#|#...#|#...#|#####|#...#|#...#|#...#",
    "I": ".###.|..#..|..#..|..#..|..#..|..#..|.###.",
    "J": "..###|...#.|...#.|...#.|...#.|#..#.|.##..",
    "K": "#...#|#..#.|#.#..|##...|#.#..|#..#.|#...#",
    "L": "#....|#....|#....|#....|#....|#....|#####",
    "M": "#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#",
    "N": "#...#|##..#|#.#.#|#..##|#...#|#...#|#...#",
    "O": ".###.|#...#|#...#|#...#|#...#|#...#|.###.",
    "P": "####.|#...#|#...#|####.|#....|#....|#....",
    "Q": ".###.|#...#|#...#|#...#|#.#.#|#..#.|.##.#",
    "R": "####.|#...#|#...#|####.|#.#..|#..#.|#...#",
    "S": ".####|#....|#....|.###.|....#|....#|####.",
    "T": "#####|..#..|..#..|..#..|..#..|..#..|..#..",
    "U": "#...#|#...#|#...#|#...#|#...#|#...#|.###.",
    "V": "#...#|#...#|#...#|#...#|#...#|.#.#.|..#..",
    "W": "#...#|#...#|#...#|#.#.#|#.#.#|##.##|#...#",
    "X": "#...#|#...#|.#.#.|..#..|.#.#.|#...#|#...#",
    "Y": "#...#|#...#|.#.#.|..#..|..#..|..#..|..#..",
    "Z": "#####|....#|...#.|..#..|.#...|#....|#####",
    "0": ".###.|#...#|#..##|#.#.#|##..#|#...#|.###.",
    "1": "..#..|.##..|..#..|..#..|..#..|..#..|.###.",
    "2": ".###.|#...#|....#|...#.|..#..|.#...|#####",
    "3": ".###.|#...#|....#|..##.|....#|#...#|.###.",
    "4": "...#.|..##.|.#.#.|#..#.|#####|...#.|...#.",
    "5": "#####|#....|####.|....#|....#|#...#|.###.",
    "6": "..##.|.#...|#....|####.|#...#|#...#|.###.",
    "7": "#####|....#|...#.|..#..|.#...|.#...|.#...",
    "8": ".###.|#...#|#...#|.###.|#...#|#...#|.###.",
    "9": ".###.|#...#|#...#|.####|....#|...#.|.##..",
    ".": ".....|.....|.....|.....|.....|.##..|.##..",
    ",": ".....|.....|.....|.....|.##..|..#..|.#...",
    "!": "..#..|..#..|..#..|..#..|..#..|.....|..#..",
    "?": ".###.|#...#|....#|...#.|..#..|.....|..#..",
    ":": ".....|.##..|.##..|.....|.##..|.##..|.....",
    "-": ".....|.....|.....|#####|.....|.....|.....",
    "+": ".....|..#..|..#..|#####|..#..|..#..|.....",
    "/": "....#|....#|...#.|..#..|.#...|#....|#....",
    "'": "..#..|..#..|.#...|.....|.....|.....|.....",
    "*": "..#..|#.#.#|.###.|#####|.###.|#.#.#|..#..",
    " ": ".....|.....|.....|.....|.....|.....|.....",
}
FONT = {k: np.array([[c == "#" for c in row] for row in v.split("|")], dtype=bool) for k, v in _G.items()}


def text_mask(s, scale=1, gap=1):
    cols = []
    for ch in s.upper():
        cols.append(FONT.get(ch, FONT["?"]))
        cols.append(np.zeros((7, gap), dtype=bool))
    m = np.concatenate(cols[:-1], axis=1)
    return np.kron(m, np.ones((scale, scale), dtype=bool))


def text_width(s, scale=1, gap=1):
    return (len(s) * (5 + gap) - gap) * scale


def blit_mask(img, mask, x, y, color, alpha=1.0):
    h, w = mask.shape
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, W), min(y + h, H)
    if x0 >= x1 or y0 >= y1 or alpha <= 0:
        return
    sub = mask[y0 - y:y1 - y, x0 - x:x1 - x]
    reg = img[y0:y1, x0:x1].astype(np.float32)
    col = np.array(color, dtype=np.float32)
    reg[sub] = reg[sub] * (1 - alpha) + col * alpha
    img[y0:y1, x0:x1] = reg.astype(np.uint8)


def text(img, s, x, y, color, scale=1, alpha=1.0, shadow=True, anchor="l", gap=1):
    m = text_mask(s, scale, gap)
    w = m.shape[1]
    if anchor == "c":
        x = x - w // 2
    elif anchor == "r":
        x = x - w
    if shadow:
        blit_mask(img, m, x + scale, y + scale, BLACK, alpha * 0.55)
    blit_mask(img, m, x, y, color, alpha)


def rect(img, x0, y0, x1, y1, color, alpha=1.0):
    x0, y0, x1, y1 = max(int(x0), 0), max(int(y0), 0), min(int(x1), W), min(int(y1), H)
    if x0 >= x1 or y0 >= y1:
        return
    reg = img[y0:y1, x0:x1].astype(np.float32)
    img[y0:y1, x0:x1] = (reg * (1 - alpha) + np.array(color, dtype=np.float32) * alpha).astype(np.uint8)


# ---------------------------------------------------------------- icons (RGBA PNGs of the pack)
def read_png(path):
    """An 8-bit RGBA, non-interlaced PNG (what make_item_icons writes) as an (h, w, 4) uint8 array; all five row filters."""
    d = path.read_bytes()
    pos, idat = 8, b""
    while pos < len(d):
        ln = int.from_bytes(d[pos:pos + 4], "big")
        typ, body = d[pos + 4:pos + 8], d[pos + 8:pos + 8 + ln]
        pos += 12 + ln
        if typ == b"IHDR":
            w, h, bit_depth, color_type, _, _, interlace = (int.from_bytes(body[:4], "big"), int.from_bytes(body[4:8], "big"), *body[8:13])
            assert (bit_depth, color_type, interlace) == (8, 6, 0), f"{path}: not 8-bit RGBA"
        elif typ == b"IDAT":
            idat += body
    raw = zlib.decompress(idat)
    stride = w * 4
    out = np.zeros((h, stride), dtype=np.int32)
    p = 0
    for y in range(h):
        f = raw[p]
        line = np.frombuffer(raw[p + 1:p + 1 + stride], dtype=np.uint8).astype(np.int32)
        p += 1 + stride
        prev = out[y - 1] if y else np.zeros(stride, dtype=np.int32)
        cur = np.zeros(stride, dtype=np.int32)
        for i in range(stride):
            a = cur[i - 4] if i >= 4 else 0
            b = prev[i]
            c = prev[i - 4] if i >= 4 else 0
            if f == 0:
                v = line[i]
            elif f == 1:
                v = line[i] + a
            elif f == 2:
                v = line[i] + b
            elif f == 3:
                v = line[i] + ((a + b) >> 1)
            else:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                v = line[i] + (a if (pa <= pb and pa <= pc) else (b if pb <= pc else c))
            cur[i] = v & 255
        out[y] = cur
    return out.reshape(h, w, 4).astype(np.uint8)


_icons = {}


def icon(name):
    if name not in _icons:
        _icons[name] = read_png(ASSETS / "textures" / "item" / name)
    return _icons[name]


def blit_rgba(img, rgba, x, y, scale=1, tint=None, alpha=1.0):
    a = np.kron(rgba, np.ones((scale, scale, 1), dtype=np.uint8))
    h, w = a.shape[:2]
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, W), min(y + h, H)
    if x0 >= x1 or y0 >= y1:
        return
    sub = a[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float32)
    rgb = sub[..., :3]
    if tint is not None:
        rgb = rgb * (np.array(tint, dtype=np.float32) / 255.0)
    al = (sub[..., 3:4] / 255.0) * alpha
    reg = img[y0:y1, x0:x1].astype(np.float32)
    img[y0:y1, x0:x1] = (reg * (1 - al) + rgb * al).astype(np.uint8)


def outline(img, rgba, x, y, scale, color=(12, 12, 14), alpha=1.0):
    """dark 1-px (scaled) border behind an icon so it reads on any background."""
    m = np.kron(rgba[..., 3] > 0, np.ones((scale, scale), dtype=bool))
    big = np.zeros((m.shape[0] + 2 * scale, m.shape[1] + 2 * scale), dtype=bool)
    for dy in (-scale, 0, scale):
        for dx in (-scale, 0, scale):
            big[scale + dy:scale + dy + m.shape[0], scale + dx:scale + dx + m.shape[1]] |= m
    blit_mask(img, big, x - scale, y - scale, color, alpha)


# ---------------------------------------------------------------- helpers
def clamp01(t):
    return max(0.0, min(1.0, t))


def ease_out(t):
    t = clamp01(t)
    return 1 - (1 - t) ** 3


def ease_back(t):
    t = clamp01(t)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


_rng = np.random.default_rng(7)
STARS = [(_rng.integers(0, W), _rng.integers(0, H), _rng.uniform(0.15, 0.7), _rng.integers(1, 3), _rng.uniform(0, 6.28))
         for _ in range(46)]
_grad = np.zeros((H, W, 3), dtype=np.uint8)
for _y in range(H):
    _t = _y / (H - 1)
    _grad[_y, :] = (int(26 + 14 * _t), int(27 + 15 * _t), int(31 + 18 * _t))


def background(n):
    img = _grad.copy()
    for (x, y, sp, sz, ph) in STARS:
        yy = int((y - sp * n) % H)
        tw = 0.35 + 0.25 * math.sin(n * 0.25 + ph)
        rect(img, x, yy, x + sz, yy + sz, PRIMARY, tw)
    return img


# ---------------------------------------------------------------- scene: title
def scene_title(n):
    img = background(n)
    sc = 5
    tw = text_width(TITLE, sc)
    x0 = (W - tw) // 2
    y0 = 52
    cw = 6 * sc
    for i, ch in enumerate(TITLE):
        t0 = 2 + i * 1.6
        if n < t0:
            continue
        flash = n - t0 < 1.5
        off = int((1 - clamp01((n - t0) / 4.0)) * -26)
        m = text_mask(ch, sc)
        col = WHITE if flash else PRIMARY
        blit_mask(img, m, x0 + i * cw + sc, y0 + off + sc, BLACK, 0.55)
        blit_mask(img, m, x0 + i * cw, y0 + off, col, 1.0)
    # accent underline sweeping
    u = ease_out((n - 18) / 8.0)
    if u > 0:
        rect(img, x0, y0 + 7 * sc + 8, x0 + int(tw * u), y0 + 7 * sc + 11, ACCENT)
    a = clamp01((n - 22) / 6.0)
    if a > 0:
        text(img, SUBTITLE, W // 2, y0 + 7 * sc + 22, SECOND, 2, alpha=a, anchor="c")
    return img


# ---------------------------------------------------------------- scene: games
def scene_games(n):
    img = background(n + 30)
    count = len(GAMES)
    k = int(count * ease_out(n / 14.0))  # counter 0 -> count
    text(img, str(k), 66, 12, ACCENT, 5, anchor="c")
    text(img, GAMES_HEADING, 208, 22, WHITE, 3, anchor="c")
    cols = 3
    rows = -(-count // cols)
    cw, rh = 100, 12
    gx0 = (W - cols * cw) // 2 + 4
    gy0 = 58
    shown = int(count * clamp01((n - 8) / 26.0))
    for i, name in enumerate(GAMES):
        if i >= shown:
            break
        c, r = divmod(i, rows)
        x, y = gx0 + c * cw, gy0 + r * rh
        col = ACCENT if shown - i <= 2 else SECOND
        rect(img, x - 3, y + 2, x - 1, y + 5, PRIMARY)
        text(img, name, x + 2, y, col, 1)
    return img


# ---------------------------------------------------------------- scene: zeichnen
CW, CH = 48, 32
_yy, _xx = np.mgrid[0:CH, 0:CW]


def ell(cx, cy, rx, ry):
    return ((_xx - cx) / rx) ** 2 + ((_yy - cy) / ry) ** 2 <= 1.0


def build_panda():
    layers = []
    full = np.ones((CH, CW), dtype=bool)
    layers.append((full, (226, 234, 252), "dist", (24, 16), 3, 9))
    bamboo = np.zeros((CH, CW), dtype=bool)
    bamboo[:, 5:7] = True
    layers.append((bamboo, (88, 166, 70), "row", None, 9, 13))
    nodes = np.zeros((CH, CW), dtype=bool)
    nodes[(np.arange(CH) % 8) == 3, 4:8] = True
    layers.append((nodes, (50, 110, 45), "row", None, 12, 14))
    ears = ell(14, 8, 4.6, 4.6) | ell(34, 8, 4.6, 4.6)
    layers.append((ears, (35, 35, 40), "angle", (24, 16), 14, 17))
    head_out = ell(24, 17, 12.6, 11.6)
    layers.append((head_out, (35, 35, 40), "angle", (24, 17), 17, 22))
    head_fill = ell(24, 17, 11.2, 10.2)
    layers.append((head_fill, (252, 252, 252), "row", None, 21, 25))
    patches = ell(18.5, 16, 3.2, 4.3) | ell(29.5, 16, 3.2, 4.3)
    layers.append((patches, (35, 35, 40), "angle", (24, 16), 25, 28))
    eyes = ell(18.8, 15.4, 1.4, 1.6) | ell(29.2, 15.4, 1.4, 1.6)
    layers.append((eyes, (255, 255, 255), "row", None, 28, 30))
    pupils = ell(19.2, 15.8, 0.7, 0.8) | ell(28.8, 15.8, 0.7, 0.8)
    layers.append((pupils, (20, 20, 24), "row", None, 29, 31))
    nose = ell(24, 20.2, 2.4, 1.5)
    mouth = np.zeros((CH, CW), dtype=bool)
    mouth[23, 22:27] = True
    mouth[22, 21] = True
    mouth[22, 27] = True
    layers.append((nose | mouth, (35, 35, 40), "row", None, 30, 33))
    cheeks = ell(14.5, 21, 2.0, 1.4) | ell(33.5, 21, 2.0, 1.4)
    layers.append((cheeks, (255, 168, 178), "row", None, 33, 35))
    prepared = []
    for mask, color, mode, ref, s, e in layers:
        ys, xs = np.nonzero(mask)
        if mode == "angle":
            key = np.arctan2(ys - ref[1], xs - ref[0])
        elif mode == "dist":
            key = np.hypot(ys - ref[1], (xs - ref[0]) * 0.7)
        else:
            key = ys * 100 + xs
        o = np.argsort(key, kind="stable")
        prepared.append((ys[o], xs[o], color, s, e))
    return prepared


PANDA = build_panda()
CANVAS_X, CANVAS_Y, CSCALE = 18, 56, 3


def scene_draw(n):
    img = background(n + 60)
    a = ease_out(n / 5.0)
    text(img, DRAW_HEADING, W // 2, 10, WHITE, 2, alpha=a, anchor="c")
    text(img, DRAW_HINT, W // 2, 30, SECOND, 1, alpha=a, anchor="c")
    # canvas frame
    fx0, fy0 = CANVAS_X - 3, CANVAS_Y - 3
    rect(img, fx0, fy0, fx0 + CW * CSCALE + 6, fy0 + CH * CSCALE + 6, PRIMARY)
    canvas = np.full((CH, CW, 3), 255, dtype=np.uint8)
    cur = None
    for ys, xs, color, s, e in PANDA:
        p = clamp01((n - s) / max(1.0, (e - s)))
        k = int(round(p * len(ys)))
        if k > 0:
            canvas[ys[:k], xs[:k]] = color
            if p < 1.0:
                cur = (xs[k - 1], ys[k - 1], color)
    big = np.kron(canvas, np.ones((CSCALE, CSCALE, 1), dtype=np.uint8))
    img[CANVAS_Y:CANVAS_Y + CH * CSCALE, CANVAS_X:CANVAS_X + CW * CSCALE] = big
    if cur is not None and a >= 1.0:
        cx = CANVAS_X + cur[0] * CSCALE + CSCALE // 2
        cy = CANVAS_Y + cur[1] * CSCALE + CSCALE // 2
        bx, by = cx - 26, cy - 8
        brush, tip = icon("zeichnen/brush.png"), icon("zeichnen/brush_paint.png")
        outline(img, brush, bx, by, 2)
        blit_rgba(img, brush, bx, by, 2)
        blit_rgba(img, tip, bx, by, 2, tint=cur[2])
    # chat
    px0, py0, px1, py1 = 178, 56, 308, 56 + CH * CSCALE
    rect(img, px0 - 2, py0 - 2, px1 + 2, py1 + 2, BG2)
    rect(img, px0 - 2, py0 - 2, px1 + 2, py0 + 10, PRIMARY)
    text(img, CHAT_HEADING, px0 + 3, py0, WHITE, 1)
    for i, (t0, who, msg, correct) in enumerate(CHAT_LINES):
        if n >= t0:
            yy = py0 + 16 + i * 12
            slide = int((1 - ease_out((n - t0) / 3.0)) * 14)
            text(img, who + ":", px0 + 3 + slide, yy, PRIMARY, 1)
            text(img, msg, px0 + 3 + slide + (len(who) + 2) * 6, yy, GREEN if correct else SECOND, 1)
    t_correct = CHAT_LINES[-1][0] + 3
    if n >= t_correct:
        text(img, CORRECT, (px0 + px1) // 2, py0 + 60, GREEN, 2, anchor="c")
        if n >= t_correct + 2:
            text(img, POINTS, (px0 + px1) // 2, py0 + 80, ACCENT, 1, anchor="c")
    return img


# ---------------------------------------------------------------- scene: features + outro
def scene_outro(n):
    img = background(n + 90)
    a = ease_out(n / 5.0)
    text(img, OUTRO_HEADING, W // 2, 12, SECOND, 2, alpha=a, anchor="c")
    sc = 3
    step = 62
    x0 = (W - step * len(FEATURES)) // 2 + (step - 16 * sc) // 2
    for i, (ic, label) in enumerate(FEATURES):
        t0 = 4 + i * 3
        if n < t0:
            continue
        p = ease_back((n - t0) / 5.0)
        bounce = int((1 - clamp01(p)) * 18)
        x = x0 + i * step
        y = 40 - bounce
        rect(img, x - 7, y - 7, x + 16 * sc + 7, y + 16 * sc + 7, BG2, 0.9)
        rect(img, x - 7, y + 16 * sc + 5, x + 16 * sc + 7, y + 16 * sc + 7, PRIMARY)
        blit_rgba(img, icon(ic), x, y, sc)
        text(img, label, x + 8 * sc, 40 + 16 * sc + 12, WHITE, 1, anchor="c")
    # logo + tagline
    if n >= 24:
        lt = ease_out((n - 24) / 5.0)
        sc2 = 4
        tw = text_width(TITLE, sc2)
        x = (W - tw) // 2
        text(img, TITLE, x, 130 - int((1 - lt) * 10), PRIMARY, sc2, alpha=lt)
        pulse = 0.5 + 0.5 * math.sin((n - 24) * 0.7)
        rect(img, x, 130 + 7 * sc2 + 4, x + tw, 130 + 7 * sc2 + 6, ACCENT, 0.6 + 0.4 * pulse)
        if n >= 29:
            text(img, TAGLINE, W // 2, 130 + 7 * sc2 + 12, SECOND, 1, anchor="c", alpha=clamp01((n - 29) / 4.0))
    return img


# ---------------------------------------------------------------- timeline
SCENE_FUNCTIONS = {"title": scene_title, "games": scene_games, "draw": scene_draw, "outro": scene_outro}
TOTAL = sum(length for _, length in SCENES)  # in SOURCE_FPS frames
FRAMES = round(TOTAL * OUT_FPS / SOURCE_FPS)  # frames of the texture


def render(n_global):
    """The frame at time `n_global` (in SOURCE_FPS frames, fractions allowed) as an (H, W, 3) uint8 array."""
    start = 0
    for i, (name, length) in enumerate(SCENES):
        if n_global < start + length:
            local = n_global - start
            img = SCENE_FUNCTIONS[name](local)
            if i > 0 and local < WIPE:
                prev_name, prev_len = SCENES[i - 1]
                old = SCENE_FUNCTIONS[prev_name](prev_len - 1)
                t = (local + 1) / WIPE
                edge = int(t * (W + 30)) - 30
                out = old.copy()
                out[:, :max(edge, 0)] = img[:, :max(edge, 0)]
                rect(out, edge, 0, edge + 14, H, PRIMARY)
                rect(out, edge + 14, 0, edge + 18, H, ACCENT)
                return out
            return img
        start += length
    return SCENE_FUNCTIONS[SCENES[-1][0]](SCENES[-1][1] - 1)


# ---------------------------------------------------------------- one global palette (median cut over every pixel of every frame)
def median_cut(colors, counts, k=256):
    boxes = [(colors, counts)]
    while len(boxes) < k:
        best, bi = -1, -1
        for i, (px, ct) in enumerate(boxes):
            if len(px) < 2:
                continue
            spread = (px.max(axis=0) - px.min(axis=0)).max()
            score = spread * math.log2(1 + ct.sum())
            if score > best:
                best, bi = score, i
        if bi < 0:
            break
        px, ct = boxes.pop(bi)
        ch = int(np.argmax(px.max(axis=0) - px.min(axis=0)))
        o = np.argsort(px[:, ch], kind="stable")
        px, ct = px[o], ct[o]
        cs = np.cumsum(ct)
        cut = int(np.searchsorted(cs, cs[-1] / 2.0))
        cut = min(max(cut, 1), len(px) - 1)
        boxes.append((px[:cut], ct[:cut]))
        boxes.append((px[cut:], ct[cut:]))
    return np.array([(px * ct[:, None]).sum(axis=0) / ct.sum() for px, ct in boxes]).round().astype(np.uint8)


def quantize(frames):
    """(palette (n, 3) uint8, index array shaped like `frames` without the color axis): every distinct color maps to its nearest palette entry."""
    f = frames.astype(np.int32)
    keys = ((f[..., 0] << 16) | (f[..., 1] << 8) | f[..., 2]).reshape(-1)
    distinct, inverse, counts = np.unique(keys, return_inverse=True, return_counts=True)
    colors = np.stack([(distinct >> 16) & 255, (distinct >> 8) & 255, distinct & 255], axis=1)
    palette = median_cut(colors.astype(np.float64), counts.astype(np.float64))
    nearest = np.zeros(len(colors), dtype=np.uint8)
    pal = palette.astype(np.int32)
    for s in range(0, len(colors), 2048):
        d = ((colors[s:s + 2048, None, :] - pal[None, :, :]) ** 2).sum(axis=2)
        nearest[s:s + 2048] = d.argmin(axis=1)
    return palette, nearest[inverse.reshape(-1)].reshape(frames.shape[:3])


# ---------------------------------------------------------------- indexed PNG
def indexed_png(palette, index):
    """An 8-bit indexed PNG (color type 3, PLTE, no transparency) of an (h, w) index array. Every row uses filter 0 (none): measured on this
    strip it deflates smaller than sub / up / average / paeth or libpng's per-row adaptive choice (242 KB vs 285-500 KB), palette indices are no gradients."""
    h, w = index.shape
    rows = np.concatenate([np.zeros((h, 1), dtype=np.uint8), index], axis=1)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", w.to_bytes(4, "big") + h.to_bytes(4, "big") + bytes([8, 3, 0, 0, 0]))
            + chunk(b"PLTE", palette.tobytes()) + chunk(b"IDAT", zlib.compress(rows.tobytes(), 9)) + chunk(b"IEND", b""))


def main():
    frames = np.stack([render(k * SOURCE_FPS / OUT_FPS) for k in range(FRAMES)])
    palette, index = quantize(frames)
    texture = ASSETS / "textures" / "item" / "trailer.png"
    texture.parent.mkdir(parents=True, exist_ok=True)
    texture.write_bytes(indexed_png(palette, index.reshape(FRAMES * H, W)))
    write_json(texture.with_name("trailer.png.mcmeta"), {"animation": {"frametime": FRAMETIME, "width": W, "height": H}})
    write_json(ASSETS / "models" / "item" / "trailer.json",
               {"parent": "minecraft:item/generated", "textures": {"layer0": "pandariamc:item/trailer"}})
    write_json(ASSETS / "items" / "trailer.json", {"model": {"type": "minecraft:model", "model": "pandariamc:item/trailer"}})
    print(f"{FRAMES} frames of {W}x{H} at {OUT_FPS} fps ({FRAMES / OUT_FPS:.1f} s), {len(palette)} colors -> {texture} ({texture.stat().st_size / 1024:.0f} KB)")
    if "--preview" in sys.argv:
        target = Path(sys.argv[sys.argv.index("--preview") + 1])
        shown = index[::9]
        columns = 5
        rows = -(-len(shown) // columns)
        sheet = np.zeros((rows * H, columns * W), dtype=np.uint8)
        for i, frame in enumerate(shown):
            sheet[(i // columns) * H:(i // columns + 1) * H, (i % columns) * W:(i % columns + 1) * W] = frame
        target.write_bytes(indexed_png(palette, sheet))
        print(f"preview: {target}")


if __name__ == "__main__":
    main()
