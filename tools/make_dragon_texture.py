#!/usr/bin/env python3
"""Recolors the Ender Dragon's entity textures into the network palette (stdlib only; PNG writer from make_item_icons.py).

The dragon is a normal entity, an item model cannot replace it: the only way to give it an own look is to override its entity textures,
so this affects EVERY dragon the client sees (also a vanilla one). Without the pack the dragon simply looks vanilla.

    python tools/make_dragon_texture.py <path to a Minecraft client jar> [--preview sheet.png]

The vanilla textures are Mojang's and are NOT kept in this repo: they are read from the client jar you pass in (any version since 1.21
has the same paths; the dragon model has not changed), recolored and written to pack/assets/minecraft/textures/entity/enderdragon/:
  dragon.png        body: the vanilla shading (luminance) mapped onto a violet ramp, alpha untouched
  dragon_eyes.png   the glowing eyes layer: mapped onto a bright network-blue ramp
Not touched: dragon_exploding.png (death animation, a gray noise mask), dragon_fireball.png.

Because only the luminance is used, every detail of the vanilla texture stays (scales, belly, wing membranes); the same script on a newer
client jar re-creates the files. `--preview sheet.png` also writes the vanilla (top) and the recolored (bottom) dragon.png and eyes, 2x, to look at.
The plugin side: freebuild/survival/CLAUDE.md (Custom-Enderdrache) in the PandariaMc repo.
"""
import struct
import sys
import zipfile
import zlib
from pathlib import Path

from make_item_icons import png

OUT = Path(__file__).resolve().parent.parent / "pack" / "assets" / "minecraft" / "textures" / "entity" / "enderdragon"
IN = "assets/minecraft/textures/entity/enderdragon/"

# (position 0..1 of the vanilla luminance, color) - network colors: dark violet shadows, primary #7289DA in the highlights
BODY = [(0.0, (0x16, 0x0C, 0x2B)), (0.25, (0x3B, 0x24, 0x73)), (0.6, (0x72, 0x5B, 0xC4)), (1.0, (0xC3, 0xB4, 0xF2))]
EYES = [(0.0, (0x4B, 0x5D, 0xA9)), (0.5, (0x72, 0x89, 0xDA)), (1.0, (0xF2, 0xF6, 0xFF))]


def decode(data):
    """A non-interlaced PNG (8-bit gray, RGB, gray+alpha, RGBA, or palette of any depth) as (width, height, [[(r, g, b, a), ...] per row])."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    pos, idat, header, plte, trns = 8, b"", None, b"", b""
    while pos < len(data):
        length, tag = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if tag == b"IHDR":
            header = struct.unpack(">IIBBBBB", body)
        elif tag == b"PLTE":
            plte = body
        elif tag == b"tRNS":
            trns = body
        elif tag == b"IDAT":
            idat += body
    width, height, depth, kind, _, _, interlace = header
    assert interlace == 0 and (depth == 8 and kind in (0, 2, 4, 6) or kind == 3 and depth in (1, 2, 4, 8)),         f"unsupported PNG (depth {depth}, type {kind}, interlace {interlace})"
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[kind]
    stride = (width * channels * depth + 7) // 8  # bytes per scanline
    step = max(1, channels * depth // 8)  # bytes per pixel for the filters
    raw = zlib.decompress(idat)
    rows, prev = [], bytearray(stride)
    for y in range(height):
        filt, line = raw[y * (stride + 1)], bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = line[i - step] if i >= step else 0
            b = prev[i]
            c = prev[i - step] if i >= step else 0
            if filt == 1:
                line[i] = (line[i] + a) & 255
            elif filt == 2:
                line[i] = (line[i] + b) & 255
            elif filt == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif filt == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        prev = line
        row = []
        for x in range(width):
            if kind == 3:
                bit = x * depth
                i = (line[bit // 8] >> (8 - depth - bit % 8)) & ((1 << depth) - 1)
                row.append(tuple(plte[i * 3:i * 3 + 3]) + (trns[i] if i < len(trns) else 255,))
                continue
            px = line[x * channels:(x + 1) * channels]
            row.append({1: (px[0],) * 3 + (255,), 3: tuple(px) + (255,), 2: (px[0],) * 3 + (px[1],), 4: tuple(px)}[channels])
        rows.append(row)
    return width, height, rows


def ramp(stops, t):
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        if t <= p1:
            f = (t - p0) / (p1 - p0)
            return tuple(round(c0[i] + (c1[i] - c0[i]) * f) for i in range(3))
    return stops[-1][1]


def recolor(rows, stops):
    """Same alpha, color = the ramp at the pixel's luminance (the vanilla dragon is dark: stretched so its brightest pixel reaches the top)."""
    lum = [[(0.299 * r + 0.587 * g + 0.114 * b) / 255 for r, g, b, a in row] for row in rows]
    top = max(max(row[x] for x, px in enumerate(rows[y]) if px[3] > 0) for y, row in enumerate(lum) if any(px[3] > 0 for px in rows[y])) or 1
    return {(x, y): ramp(stops, min(1.0, lum[y][x] / top)) + (rows[y][x][3],) for y in range(len(rows)) for x in range(len(rows[y]))}


def preview(target, pairs):
    scale, bg = 2, (0x36, 0x39, 0x3F, 255)
    width = max(w for w, _, _, _ in pairs.values())
    sheet, height = {}, 0
    for original, (w, h, old, new) in pairs.items():
        for y in range(h):
            for x in range(w):
                for dx, source in ((0, old[y][x]), (width, new[(x, y)])):
                    # composite on the background so alpha is visible as the gray
                    a = source[3] / 255
                    color = tuple(round(source[i] * a + bg[i] * (1 - a)) for i in range(3)) + (255,)
                    sheet[(x + dx, y + height)] = color
        height += h
    full = {(x, y): sheet.get((x // scale, y // scale), bg) for y in range(height * scale) for x in range(2 * width * scale)}
    target.write_bytes(png(2 * width * scale, height * scale, full))
    print(f"preview: {target} (vanilla left, recolored right)")


def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith("--"):
        sys.exit("usage: python tools/make_dragon_texture.py <client.jar> [--preview sheet.png]")
    OUT.mkdir(parents=True, exist_ok=True)
    pairs = {}
    with zipfile.ZipFile(sys.argv[1]) as jar:
        for name, stops in (("dragon.png", BODY), ("dragon_eyes.png", EYES)):
            width, height, rows = decode(jar.read(IN + name))
            canvas = recolor(rows, stops)
            (OUT / name).write_bytes(png(width, height, canvas))
            print(f"wrote {OUT / name} ({width}x{height})")
            pairs[name] = (width, height, rows, canvas)
    if "--preview" in sys.argv:
        preview(Path(sys.argv[sys.argv.index("--preview") + 1]), pairs)


if __name__ == "__main__":
    main()
