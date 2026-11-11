#!/usr/bin/env python3
"""Generates the Tower Defense models of the PandariaMc server pack (stdlib only, reproducible - no randomness).

Every model is a handful of cuboids ("boxes") with a 16x16 texture of colour cells: 4x4 cells of 4x4 px, one per colour the model
uses, each shaded like a vanilla block (light top-left edge, dark bottom-right edge, a fixed dither). A face shows its box's cell
stretched over it, so it reads as chunky pixel art in the network palette. Hand-painted textures can replace the PNGs later: keep the
cell layout (or edit the uv in the model json) and the ids.

Output (default: assets/pandariamc next to this script; --out DIR = another assets/pandariamc folder, e.g. the Resourcepack repo's
pack/assets/pandariamc), for every <name> below:
  items/towerdefense/<name>.json             item definition -> id pandariamc:towerdefense/<name>
  models/item/towerdefense/<name>.json       the cuboid model
  textures/item/towerdefense/<name>.png      16x16 colour cells

Model space: 0..16 per axis, the model stands on y = 0 centred on x = z = 8 and looks along +Z (its "south" face is the front). The
plugin (games/towerdefense, view/EnemyBodies, TowerBodies) shows them in ItemDisplays and lifts them by half their scale. "gui" display
settings make the towers usable as menu icons.

Run: py -3 tools/make_towerdefense_assets.py [--out DIR]  (copy of games/towerdefense/pack/ in the PandariaMc repo)
"""
import json
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Network palette (api:text Colors) plus darker/lighter steps of it.
C = {
    "primary": (0x72, 0x89, 0xDA), "primary_dark": (0x4B, 0x5D, 0xA9), "primary_light": (0xA9, 0xB8, 0xF0),
    "secondary": (0xB5, 0xBA, 0xC1), "gray": (0x80, 0x84, 0x8E), "dark": (0x2B, 0x2D, 0x31), "black": (0x1E, 0x1F, 0x22),
    "accent": (0xFE, 0xE7, 0x5C), "accent_dark": (0xC4, 0xA9, 0x2E),
    "red": (0xED, 0x42, 0x45), "red_dark": (0xA8, 0x2E, 0x31), "red_deep": (0x5E, 0x16, 0x18),
    "green": (0x57, 0xF2, 0x87), "green_dark": (0x23, 0xA8, 0x52), "green_deep": (0x10, 0x5A, 0x2A),
    "white": (0xF2, 0xF3, 0xF5), "ice": (0xC6, 0xE8, 0xFF), "cyan": (0x6F, 0xD8, 0xF2),
    "wood": (0x93, 0x65, 0x30), "wood_dark": (0x5A, 0x3C, 0x1A), "copper": (0xC8, 0x6B, 0x3C), "stone": (0x6B, 0x6E, 0x75),
}


def box(frm, to, color, rotation=None):
    return {"from": frm, "to": to, "color": color, "rotation": rotation}


# --- the models: name -> boxes (front = +Z) ---

def humanoid(body, head, legs, eyes, wide=0):
    return [
        box([5 - wide, 0, 7], [7 - wide / 2, 3, 9], legs), box([9 + wide / 2, 0, 7], [11 + wide, 3, 9], legs),
        box([4 - wide, 3, 5], [12 + wide, 10, 11], body),
        box([5, 10, 6], [11, 15, 10], head),
        box([6, 12, 10], [7.5, 13.5, 10.5], eyes), box([8.5, 12, 10], [10, 13.5, 10.5], eyes),
    ]


MODELS = {
    "enemy_laeufer": humanoid("red", "red_dark", "dark", "accent"),
    "enemy_flitzer": [
        box([5, 1, 4], [11, 5, 13], "accent"), box([6, 5, 5], [7, 8, 7], "accent_dark"), box([9, 5, 5], [10, 8, 7], "accent_dark"),
        box([5.5, 0, 5], [7, 1, 7], "dark"), box([9, 0, 5], [10.5, 1, 7], "dark"), box([5.5, 0, 10], [7, 1, 12], "dark"),
        box([9, 0, 10], [10.5, 1, 12], "dark"), box([6, 3, 13], [7.5, 4.5, 13.5], "red"), box([8.5, 3, 13], [10, 4.5, 13.5], "red"),
    ],
    "enemy_panzer": [
        box([2, 2, 2], [14, 7, 14], "primary_dark"), box([3, 7, 3], [13, 9, 13], "gray"), box([7.5, 7, 2], [8.5, 9.5, 14], "dark"),
        box([5, 2, 14], [11, 6, 16], "dark"), box([6, 4, 16], [7, 5, 16.5], "red"), box([9, 4, 16], [10, 5, 16.5], "red"),
        box([1, 0, 4], [2, 3, 5], "dark"), box([1, 0, 8], [2, 3, 9], "dark"), box([1, 0, 12], [2, 3, 13], "dark"),
        box([14, 0, 4], [15, 3, 5], "dark"), box([14, 0, 8], [15, 3, 9], "dark"), box([14, 0, 12], [15, 3, 13], "dark"),
    ],
    "enemy_flatterer": [
        box([6, 5, 6], [10, 10, 10], "primary_dark"), box([0, 8, 7], [6, 9, 10], "primary"), box([10, 8, 7], [16, 9, 10], "primary"),
        box([1, 7, 7], [3, 8, 9], "primary_dark"), box([13, 7, 7], [15, 8, 9], "primary_dark"),
        box([6.5, 8, 10], [7.5, 9, 10.5], "accent"), box([8.5, 8, 10], [9.5, 9, 10.5], "accent"),
        box([6.5, 10, 7], [7.5, 12, 8], "primary_dark"), box([8.5, 10, 7], [9.5, 12, 8], "primary_dark"),
    ],
    "enemy_schemen": [
        box([4, 2, 5], [12, 14, 11], "secondary"), box([4, 0, 5], [6, 2, 7], "secondary"), box([7, 0, 8], [9, 2, 10], "secondary"),
        box([10, 0, 5], [12, 2, 7], "secondary"), box([5.5, 10, 11], [7.5, 12, 11.5], "black"), box([8.5, 10, 11], [10.5, 12, 11.5], "black"),
        box([6.5, 7, 11], [9.5, 8, 11.5], "dark"), box([2, 6, 7], [4, 10, 9], "gray"), box([12, 6, 7], [14, 10, 9], "gray"),
    ],
    "enemy_heiler": humanoid("green_dark", "white", "green_deep", "dark") + [
        box([7, 4, 11], [9, 9, 11.5], "white"), box([5.5, 5.75, 11], [10.5, 7.25, 11.5], "white"),
        box([12, 3, 7], [13, 14, 8], "wood"), box([11.5, 14, 6.5], [13.5, 16, 8.5], "green"),
    ],
    "enemy_brutknoten": [
        box([3, 0, 3], [13, 9, 13], "green_dark"), box([4, 9, 4], [12, 11, 12], "green"), box([2, 3, 5], [3, 7, 9], "green"),
        box([13, 2, 6], [14, 6, 10], "green"), box([6, 11, 6], [10, 12, 10], "green_deep"),
        box([5, 5, 13], [6.5, 6.5, 13.5], "accent"), box([7.5, 6, 13], [8.5, 7, 13.5], "accent"), box([9.5, 5, 13], [11, 6.5, 13.5], "accent"),
        box([6, 2, 13], [10, 3, 13.5], "green_deep"),
    ],
    "enemy_koloss": humanoid("stone", "gray", "dark", "red", wide=2) + [
        box([0, 4, 6], [2, 12, 10], "stone"), box([14, 4, 6], [16, 12, 10], "stone"), box([4, 9, 4], [12, 11, 12], "gray"),
    ],
    "enemy_golem": humanoid("dark", "stone", "black", "accent", wide=2) + [
        box([0, 3, 6], [2, 12, 10], "dark"), box([14, 3, 6], [16, 12, 10], "dark"),
        box([6, 5, 11], [7, 9, 11.5], "accent_dark"), box([9, 4, 11], [10, 8, 11.5], "accent_dark"),
        box([5, 15, 7], [6, 16, 8], "accent"), box([7.5, 15, 7], [8.5, 16, 8], "accent"), box([10, 15, 7], [11, 16, 8], "accent"),
    ],
    "enemy_koenigin": [
        box([4, 2, 0], [12, 8, 8], "red_deep"), box([5, 3, 8], [11, 9, 12], "red_dark"), box([6, 5, 12], [10, 10, 16], "red"),
        box([6, 10, 13], [10, 11, 15], "accent"), box([6, 11, 13], [7, 12.5, 14], "accent"), box([9, 11, 13], [10, 12.5, 14], "accent"),
        box([6.5, 7, 16], [7.5, 8, 16.5], "accent"), box([8.5, 7, 16], [9.5, 8, 16.5], "accent"),
        box([1, 9, 2], [7, 10, 10], "secondary"), box([9, 9, 2], [15, 10, 10], "secondary"),
        box([3, 0, 9], [5, 4, 10], "black"), box([11, 0, 9], [13, 4, 10], "black"), box([3, 0, 5], [5, 3, 6], "black"),
        box([11, 0, 5], [13, 3, 6], "black"),
    ],
    "tower_bolzen": [
        box([3, 0, 3], [13, 4, 13], "stone"), box([6, 4, 6], [10, 10, 10], "wood"), box([3, 10, 6], [13, 12, 10], "wood_dark"),
        box([2, 11, 7], [3, 13, 9], "wood_dark"), box([13, 11, 7], [14, 13, 9], "wood_dark"),
        box([7.5, 12, 4], [8.5, 13, 15], "wood"), box([7, 11.75, 15], [9, 13.25, 16], "secondary"),
    ],
    "tower_kanone": [
        box([2, 0, 2], [14, 3, 14], "dark"), box([4, 3, 4], [12, 9, 12], "gray"), box([6, 5, 10], [10, 9, 16], "black"),
        box([5.5, 4.5, 14], [10.5, 9.5, 15], "dark"), box([3, 3, 6], [4, 7, 10], "wood_dark"), box([12, 3, 6], [13, 7, 10], "wood_dark"),
    ],
    "tower_frost": [
        box([3, 0, 3], [13, 3, 13], "white"), box([5, 3, 5], [11, 10, 11], "ice"),
        box([6, 10, 6], [10, 16, 10], "cyan", {"angle": 45, "axis": "y", "origin": [8, 8, 8]}),
        box([4, 8, 7], [5, 12, 9], "cyan"), box([11, 8, 7], [12, 12, 9], "cyan"),
    ],
    "tower_blitz": [
        box([3, 0, 3], [13, 3, 13], "copper"), box([6, 3, 6], [10, 12, 10], "copper"), box([5, 5, 5], [11, 6, 11], "accent_dark"),
        box([5, 8, 5], [11, 9, 11], "accent_dark"), box([5, 12, 5], [11, 16, 11], "accent"), box([7, 16, 7], [9, 16.5, 9], "white"),
    ],
    "tower_scharf": [
        box([4, 0, 4], [12, 3, 12], "dark"), box([6, 3, 6], [10, 11, 10], "gray"), box([5, 11, 5], [11, 13, 11], "dark"),
        box([7, 13, 2], [9, 15, 16], "black"), box([7.25, 13.25, 16], [8.75, 14.75, 16.25], "primary_light"),
        box([7.5, 15, 7], [8.5, 16, 9], "red"),
    ],
    "tower_verstaerker": [
        box([3, 0, 3], [13, 3, 13], "primary_dark"), box([6, 3, 6], [10, 12, 10], "white"),
        box([5, 12, 5], [11, 16, 11], "primary", {"angle": 45, "axis": "y", "origin": [8, 14, 8]}),
        box([4, 6, 7], [6, 10, 9], "primary_light"), box([10, 6, 7], [12, 10, 9], "primary_light"),
    ],
    "tower_goldmine": [
        box([2, 0, 3], [14, 4, 13], "wood"), box([2, 4, 3], [14, 5, 4], "wood_dark"), box([2, 4, 12], [14, 5, 13], "wood_dark"),
        box([4, 4, 5], [12, 8, 11], "accent"), box([6, 8, 6], [10, 10, 10], "accent_dark"), box([12.5, 4, 8], [13.5, 13, 9], "wood_dark"),
        box([10, 12, 8], [16, 13.5, 9], "gray"),
    ],
    "shot_bolt": [
        box([7.5, 7.5, 2], [8.5, 8.5, 14], "wood"), box([7, 7, 14], [9, 9, 16], "secondary"), box([7.5, 6, 2], [8.5, 10, 4], "white"),
    ],
    "shot_ball": [
        box([5, 5, 5], [11, 11, 11], "black"), box([6, 9, 6], [8, 11, 8], "gray"),
    ],
    "core": [
        box([5, 0, 5], [11, 12, 11], "primary", {"angle": 45, "axis": "y", "origin": [8, 6, 8]}),
        box([6, 2, 6], [10, 15, 10], "primary_light"), box([4, 0, 4], [12, 2, 12], "primary_dark"),
    ],
}


# --- texture + json ---

def shade(color, factor):
    return tuple(max(0, min(255, round(v * factor))) for v in color)


def texture(colors):
    """16x16 RGBA: cell n = (n % 4, n // 4), each 4x4 px shaded."""
    pixels = {}
    for n, name in enumerate(colors):
        base = C[name]
        cx, cy = (n % 4) * 4, (n // 4) * 4
        for y in range(4):
            for x in range(4):
                if x == 0 or y == 0:
                    factor = 1.18
                elif x == 3 or y == 3:
                    factor = 0.78
                else:
                    factor = 1.0 if (x + y) % 2 == 0 else 0.92
                pixels[(cx + x, cy + y)] = shade(base, factor) + (255,)
    return pixels


def png(width, height, pixels):
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"".join(bytes(pixels.get((x, y), (0, 0, 0, 0))) for x in range(width)) for y in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


DISPLAY = {
    "gui": {"rotation": [30, 225, 0], "translation": [0, 0, 0], "scale": [0.625, 0.625, 0.625]},
    "ground": {"rotation": [0, 0, 0], "translation": [0, 3, 0], "scale": [0.25, 0.25, 0.25]},
    "fixed": {"rotation": [0, 0, 0], "translation": [0, 0, 0], "scale": [0.5, 0.5, 0.5]},
    "thirdperson_righthand": {"rotation": [75, 45, 0], "translation": [0, 2.5, 0], "scale": [0.375, 0.375, 0.375]},
    "firstperson_righthand": {"rotation": [0, 45, 0], "translation": [0, 0, 0], "scale": [0.4, 0.4, 0.4]},
}


def model(name, boxes):
    colors = list(dict.fromkeys(b["color"] for b in boxes))
    assert len(colors) <= 16, f"{name}: more than 16 colours"
    elements = []
    for b in boxes:
        n = colors.index(b["color"])
        u, v = (n % 4) * 4, (n // 4) * 4
        assert all(-16 <= c <= 32 for c in b["from"] + b["to"]), f"{name}: element out of range"
        face = {"uv": [u, v, u + 4, v + 4], "texture": "#0"}
        element = {"from": b["from"], "to": b["to"],
                   "faces": {side: dict(face) for side in ("north", "east", "south", "west", "up", "down")}}
        if b["rotation"]:
            element["rotation"] = b["rotation"]
        elements.append(element)
    texture_id = f"pandariamc:item/towerdefense/{name}"
    return colors, {"textures": {"0": texture_id, "particle": texture_id}, "elements": elements, "display": DISPLAY}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8", newline="\n")


def main():
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else HERE.parent / "pack" / "assets" / "pandariamc"
    for name, boxes in MODELS.items():
        colors, data = model(name, boxes)
        write_json(out / "models" / "item" / "towerdefense" / f"{name}.json", data)
        write_json(out / "items" / "towerdefense" / f"{name}.json",
                   {"model": {"type": "minecraft:model", "model": f"pandariamc:item/towerdefense/{name}"}})
        png_path = out / "textures" / "item" / "towerdefense" / f"{name}.png"
        png_path.parent.mkdir(parents=True, exist_ok=True)
        png_path.write_bytes(png(16, 16, texture(colors)))
    print(f"{len(MODELS)} models written to {out}")


if __name__ == "__main__":
    main()
