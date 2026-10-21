#!/usr/bin/env python3
"""Generates the target discs of the Zielschmettern minigame (stdlib only; PNG/JSON helpers from make_item_icons.py).

Item models (ItemDisplays in the game), all under pack/assets/pandariamc/ - the ids are `pandariamc:zielschmettern/<name>`:
  target_big     red bull's-eye on white, gold center         (x1.0, 7 blocks wide in the game)
  target_small   blue bull's-eye on white, gold center        (x1.5, 3.5 blocks)
  target_moving  green bull's-eye, arrow marks, dashed rim    (x2.0, 5 blocks, swings)
each as items/zielschmettern/<name>.json + models/item/zielschmettern/<name>.json (child of the shared flat two-sided quad
models/item/zielschmettern/disc.json) + textures/item/zielschmettern/<name>.png (64x64, the disc fills the square edge to edge,
the corners are transparent, alpha is only 0 or 255).

How the plugin lays it flat (games/zielschmettern/Targets.java): the quad stands in the XY plane, front (+Z) towards the viewer,
one block big. The ItemDisplay transformation turns it -90 degrees around X (front = up, the player looks down on it from above)
and scales it to (diameter, diameter, 1). Both faces are drawn, so it reads right from below, too.

The rings are the scoring rings: the border between the gold center and the colored ring is at 35 % of the radius (= Tuning.RING_INNER,
the full 1.0 points), the border between the colored and the white ring at 70 % (= RING_MIDDLE, 0.7 points), the white ring is the
outer 0.4. Change Tuning.RING_* in the game = change RING_INNER / RING_MIDDLE here.

The plugin side: games/zielschmettern/CLAUDE.md in the PandariaMc repo. Re-run after editing a color; `--preview sheet.png` also
writes a 4x contact sheet of the three discs to look at.
"""
import math
import struct
import sys
import zlib
from pathlib import Path

from make_item_icons import ASSETS, png, write_json

SIZE = 64
RING_INNER = 0.35  # Tuning.RING_INNER
RING_MIDDLE = 0.70  # Tuning.RING_MIDDLE
LINE = 0.035  # width of the dark borders between the rings, as a fraction of the radius
OUTLINE = 0.04  # dark rim around the disc

DARK = (0x1E, 0x1F, 0x22)
WHITE = (0xF2, 0xF3, 0xF5)
GOLD = (0xFE, 0xE7, 0x5C)  # network accent
DEEP = (0x2B, 0x2D, 0x31)
# name, ring color (the middle zone), spot color (the dot in the center)
KINDS = [
    ("big", (0xED, 0x42, 0x45), (0xED, 0x42, 0x45)),  # network error red
    ("small", (0x72, 0x89, 0xDA), (0x4B, 0x5D, 0xA9)),  # network primary
    ("moving", (0x57, 0xF2, 0x87), (0x1F, 0x8F, 0x4D)),  # network success green
]


def rgba(color):
    return tuple(color) + (255,)


def arrow(canvas, cx, cy, dx, dy, color):
    """A small filled triangle at (cx, cy) pointing along (dx, dy) (one of the four axis directions), 5 px long."""
    for step in range(5):
        for side in range(-(4 - step), 5 - step):
            x, y = (cx + dx * step - dy * side, cy + dy * step + dx * side)
            canvas[(x, y)] = rgba(color)


def disc(name, ring, spot):
    """The 64x64 canvas of one target kind."""
    canvas = {}
    c = (SIZE - 1) / 2
    for y in range(SIZE):
        for x in range(SIZE):
            r = math.hypot(x - c, y - c) / (SIZE / 2)
            if r > 1.0:
                continue
            if r > 1.0 - OUTLINE:
                color = DARK
            elif abs(r - RING_MIDDLE) <= LINE / 2 or abs(r - RING_INNER) <= LINE / 2:
                color = DARK
            elif r > RING_MIDDLE:
                color = WHITE
            elif r > RING_INNER:
                color = ring
            else:
                color = spot if r <= 0.08 else GOLD
            canvas[(x, y)] = rgba(color)
    if name == "moving":
        # Motion marks: a dashed dark rim (every other 10 degree segment is gold) and four arrows on the white ring.
        for y in range(SIZE):
            for x in range(SIZE):
                r = math.hypot(x - c, y - c) / (SIZE / 2)
                if 1.0 - OUTLINE * 2.2 < r <= 1.0 - OUTLINE and int(math.degrees(math.atan2(y - c, x - c)) % 360 // 10) % 2 == 0:
                    canvas[(x, y)] = rgba(GOLD)
        mid = (RING_MIDDLE + 1.0 - OUTLINE) / 2 * (SIZE / 2)  # radius of the middle of the white ring
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            arrow(canvas, round(c + dx * (mid - 2)), round(c + dy * (mid - 2)), dx, dy, DEEP)
    return canvas


def write_asset(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def write_all():
    base = ASSETS / "models" / "item" / "zielschmettern"
    # A flat quad readable from both sides (an ItemDisplay may turn the model around); the plugin lays it flat and scales it.
    # The two faces sit 0.02 apart so they never z-fight, whether back faces are culled or not (same trick as tastentakt's cap.json).
    write_json(base / "disc.json", {"elements": [
        {"from": [0, 0, z], "to": [16, 16, z], "shade": False, "faces": {side: {"uv": [0, 0, 16, 16], "texture": "#layer0"}}}
        for side, z in (("south", 8.01), ("north", 7.99))
    ]})
    canvases = {}
    for name, ring, spot in KINDS:
        canvases[name] = disc(name, ring, spot)
        write_asset(ASSETS / "textures" / "item" / "zielschmettern" / f"target_{name}.png", png(SIZE, SIZE, canvases[name]))
        write_json(base / f"target_{name}.json", {"parent": "pandariamc:item/zielschmettern/disc",
                                                  "textures": {"layer0": f"pandariamc:item/zielschmettern/target_{name}"}})
        write_json(ASSETS / "items" / "zielschmettern" / f"target_{name}.json",
                   {"model": {"type": "minecraft:model", "model": f"pandariamc:item/zielschmettern/target_{name}"}})
    verify()
    print(f"{len(KINDS)} targets written to {ASSETS}")
    return canvases


def verify():
    """Every id has its item json, model json and a PNG that decodes (signature, CRCs, size, only alpha 0 / 255)."""
    for name, _, _ in KINDS:
        for path in (ASSETS / "items" / "zielschmettern" / f"target_{name}.json",
                     ASSETS / "models" / "item" / "zielschmettern" / f"target_{name}.json"):
            assert path.is_file(), f"missing {path}"
        data = (ASSETS / "textures" / "item" / "zielschmettern" / f"target_{name}.png").read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{name}: not a PNG"
        pos, idat = 8, b""
        while pos < len(data):
            length, tag = struct.unpack(">I4s", data[pos:pos + 8])
            body = data[pos + 8:pos + 8 + length]
            assert struct.unpack(">I", data[pos + 8 + length:pos + 12 + length])[0] == zlib.crc32(tag + body) & 0xFFFFFFFF, f"{name}: bad CRC"
            if tag == b"IHDR":
                assert struct.unpack(">II", body[:8]) == (SIZE, SIZE), f"{name}: wrong size"
            if tag == b"IDAT":
                idat += body
            pos += 12 + length
        raw = zlib.decompress(idat)
        stride = 1 + SIZE * 4
        assert len(raw) == SIZE * stride, f"{name}: wrong data length"
        alphas = {raw[row * stride + 1 + col * 4 + 3] for row in range(SIZE) for col in range(SIZE)}
        assert alphas <= {0, 255}, f"{name}: translucent pixels {alphas}"


def preview(target, canvases):
    gap, scale, sheet = 6, 4, {}
    for n, name in enumerate(canvases):
        for (x, y), color in canvases[name].items():
            sheet[(x + gap + n * (SIZE + gap), y + gap)] = color
    w, h = gap + len(canvases) * (SIZE + gap), SIZE + 2 * gap
    bg = (0x36, 0x39, 0x3F, 255)
    full = {(x, y): sheet.get((x // scale, y // scale), bg) for y in range(h * scale) for x in range(w * scale)}
    target.write_bytes(png(w * scale, h * scale, full))
    print(f"preview: {target}")


def main():
    canvases = write_all()
    if "--preview" in sys.argv:
        preview(Path(sys.argv[sys.argv.index("--preview") + 1]), canvases)


if __name__ == "__main__":
    main()
