#!/usr/bin/env python3
"""Generates the pack font `pandariamc:logo_banner`: the PandariaMC logo picture in the tab list header (needs Pillow).

Source: tools/source/pandariamc_logo.webp (2000x667, painted logo on a pure black background). The black void around the
logo is made transparent by a flood fill from the border (dark outlines inside the letters stay), the picture is resampled to
480x160 and cut into two 240x160 cells side by side = glyphs U+E500 (left) and U+E501 (right); U+E502 is a space glyph of -1
(every bitmap glyph advances width + 1, the space closes that gap). Both glyphs: height 40, ascent 7 (top edge = top of the
text line) -> scale 160 -> 40 = 0.25, a glyph shows 60x40 GUI px, the whole logo 120x40 (all exact in binary, no rounding gap).
Written: pack/assets/pandariamc/font/logo_banner.json + textures/font/logo_banner_{0,1}.png. Idempotent.
`--preview OUT.png` also writes a mock of a tab list header (translucent dark panel, GUI scale 3) over a light and a dark backdrop.
Client limits (a glyph cell is at most 256x256 px, ascent <= height) are why it is two cells.
"""
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter
except ImportError:
    sys.exit("make_logo_banner.py needs Pillow: pip install pillow")

from make_item_icons import ASSETS, write_json

SOURCE = Path(__file__).resolve().parent / "source" / "pandariamc_logo.webp"
CELL_W, CELL_H = 240, 160
HEIGHT = 40  # displayed height in GUI px = CELL_H * 0.25
DARK = 14  # a border-connected pixel whose brightest channel is <= this is void


def cut_out(src):
    """RGBA of the source with the border-connected near-black void transparent (soft 1 px edge)."""
    rgb = src.convert("RGB")
    w, h = rgb.size
    dark = rgb.point(lambda v: 255 if v <= DARK else 0).split()
    mask = Image.merge("RGB", dark).convert("L").point(lambda v: 255 if v == 255 else 0)  # all three channels dark
    # floodfill needs a colour that differs from both states: 128 = void connected to the border
    for seed in [(x, y) for x in (0, w - 1) for y in range(0, h, 20)] + [(x, y) for y in (0, h - 1) for x in range(0, w, 20)]:
        if mask.getpixel(seed) == 255:
            ImageDraw.floodfill(mask, seed, 128)
    alpha = mask.point(lambda v: 0 if v == 128 else 255).filter(ImageFilter.GaussianBlur(0.8))
    out = rgb.convert("RGBA")
    out.putalpha(alpha)
    return out


def main():
    preview = None
    if "--preview" in sys.argv:
        preview = Path(sys.argv[sys.argv.index("--preview") + 1])
    img = cut_out(Image.open(SOURCE)).resize((2 * CELL_W, CELL_H), Image.LANCZOS)  # 2000x667 -> 3.0:1 (0.05 % off)
    cells = []
    for i in range(2):
        cell = img.crop((i * CELL_W, 0, (i + 1) * CELL_W, CELL_H)).quantize(256, Image.FASTOCTREE, dither=Image.NONE)
        path = ASSETS / "textures" / "font" / f"logo_banner_{i}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        cell.save(path, optimize=True)
        print(f"{path.name}: {path.stat().st_size} bytes")
        cells.append(cell.convert("RGBA"))
    write_json(ASSETS / "font" / "logo_banner.json", {"providers": [
        {"type": "bitmap", "file": f"pandariamc:font/logo_banner_{i}.png", "ascent": 7, "height": HEIGHT, "chars": [chr(0xE500 + i)]}
        for i in range(2)
    ] + [{"type": "space", "advances": {"": -1}}]})
    if preview:
        write_preview(cells, preview)


def write_preview(cells, out):
    scale, panel_w = 3, 300
    logo_w = 2 * CELL_W // 4
    lines = ["", "26.10.2026 - 21:04 ৹ 12 / 100", "", "Du befindest dich auf: lobby", ""]
    panel_h = HEIGHT + 5 + 9 * len(lines)
    sheet = Image.new("RGBA", (2 * panel_w * scale + 3 * 10 * scale, (panel_h + 20) * scale), (0, 0, 0, 255))
    for n, backdrop in enumerate(((200, 200, 205, 255), (40, 70, 40, 255))):
        x0 = (10 + n * (panel_w + 10)) * scale
        panel = Image.new("RGBA", (panel_w * scale, (panel_h + 20) * scale), backdrop)
        shade = Image.new("RGBA", (panel_w * scale, panel_h * scale), (0, 0, 0, 128))
        panel.alpha_composite(shade, (0, 10 * scale))
        logo = Image.new("RGBA", (2 * CELL_W, CELL_H))
        for i, c in enumerate(cells):
            logo.alpha_composite(c, (i * CELL_W, 0))
        logo = logo.resize((logo_w * scale, HEIGHT * scale), Image.LANCZOS)
        panel.alpha_composite(logo, ((panel_w - logo_w) * scale // 2, 10 * scale))
        draw = ImageDraw.Draw(panel)
        for k, line in enumerate(lines):
            y = (10 + HEIGHT + 5 + 9 * k) * scale
            w = draw.textlength(line)
            draw.text(((panel_w * scale - w) / 2, y), line, fill=(114, 137, 218, 255))
        sheet.alpha_composite(panel, (x0, 0))
    sheet.convert("RGB").save(out)
    print("preview:", out)


if __name__ == "__main__":
    main()
