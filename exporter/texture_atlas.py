"""Generates an original, procedurally-painted pixel-art texture atlas for
voxel blocks (grass, dirt, stone, wood, leaves, ...) -- no copyrighted
Minecraft assets, just noise-speckled tiles in the same spirit.

The atlas is a single small PNG laid out as a grid of square tiles. Every
block in the scene samples from this one image, so no matter how many
blocks are placed, the glTF export only ever needs ONE shared texture and
material -- the same reuse story as the color variant sets, one level down
at the pixel level.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image

TILE_SIZE = 32
ATLAS_COLS = 5
ATLAS_ROWS = 4

TILE_INDEX = {
    "grass_top": 0,
    "grass_side": 1,
    "dirt": 2,
    "stone": 3,
    "planks": 4,
    "log_side": 5,
    "log_top": 6,
    "leaves": 7,
    "brick": 8,
    "sand": 9,
    "water": 10,
    "cobblestone": 11,
    "snow": 12,
    "glass": 13,
    "gravel": 14,
    "orange": 15,
    "teal": 16,
    "charcoal": 17,
}

# block type name -> which tile each face samples ("side" covers all 4 walls)
BLOCK_FACES = {
    "grass": {"top": "grass_top", "bottom": "dirt", "side": "grass_side"},
    "dirt": {"top": "dirt", "bottom": "dirt", "side": "dirt"},
    "stone": {"top": "stone", "bottom": "stone", "side": "stone"},
    "cobblestone": {"top": "cobblestone", "bottom": "cobblestone", "side": "cobblestone"},
    "planks": {"top": "planks", "bottom": "planks", "side": "planks"},
    "log": {"top": "log_top", "bottom": "log_top", "side": "log_side"},
    "leaves": {"top": "leaves", "bottom": "leaves", "side": "leaves"},
    "brick": {"top": "brick", "bottom": "brick", "side": "brick"},
    "sand": {"top": "sand", "bottom": "sand", "side": "sand"},
    "water": {"top": "water", "bottom": "water", "side": "water"},
    "snow": {"top": "snow", "bottom": "dirt", "side": "snow"},
    "glass": {"top": "glass", "bottom": "glass", "side": "glass"},
    "gravel": {"top": "gravel", "bottom": "gravel", "side": "gravel"},
    "orange": {"top": "orange", "bottom": "orange", "side": "orange"},
    "teal": {"top": "teal", "bottom": "teal", "side": "teal"},
    "charcoal": {"top": "charcoal", "bottom": "charcoal", "side": "charcoal"},
}

# rough flat average color per block type, used only as a USD-side
# displayColor fallback (e.g. Quick Look) where the atlas texture doesn't apply
BLOCK_AVERAGE_COLOR = {
    "grass": (0.35, 0.55, 0.20),
    "dirt": (0.45, 0.30, 0.16),
    "stone": (0.5, 0.5, 0.5),
    "cobblestone": (0.45, 0.45, 0.47),
    "planks": (0.72, 0.55, 0.32),
    "log": (0.42, 0.28, 0.14),
    "leaves": (0.20, 0.42, 0.13),
    "brick": (0.62, 0.28, 0.20),
    "sand": (0.87, 0.80, 0.60),
    "water": (0.20, 0.42, 0.65),
    "snow": (0.92, 0.94, 0.96),
    "glass": (0.78, 0.92, 0.92),
    "gravel": (0.52, 0.48, 0.45),
    "orange": (0.97, 0.41, 0.0),
    "teal": (0.0, 0.54, 0.58),
    "charcoal": (0.13, 0.13, 0.14),
}


def _noise(rng, shape, scale=1.0):
    return (rng.random(shape) - 0.5) * scale


def _fill(rng, base_rgb, variance=14, cell=1):
    """Solid color with per-pixel (or per-cell, for a chunkier look) noise."""
    h = w = TILE_SIZE
    ch, cw = -(-h // cell), -(-w // cell)  # ceil division so the repeat always covers h/w
    noise = rng.integers(-variance, variance + 1, size=(ch, cw, 1))
    noise = np.repeat(np.repeat(noise, cell, axis=0), cell, axis=1)[:h, :w]
    arr = np.array(base_rgb, dtype=np.int16).reshape(1, 1, 3) + noise
    return np.clip(arr, 0, 255).astype(np.uint8)


def _grass_top(rng):
    return _fill(rng, (86, 148, 58), variance=18, cell=2)


def _grass_side(rng):
    dirt = _fill(rng, (117, 79, 42), variance=14, cell=2)
    grass_band = _fill(rng, (86, 148, 58), variance=18, cell=2)
    band_h = TILE_SIZE // 4
    out = dirt.copy()
    out[:band_h] = grass_band[:band_h]
    # a ragged bottom edge on the grass band, not a razor-sharp line
    for x in range(TILE_SIZE):
        dip = int(rng.integers(0, 3))
        out[band_h - dip:band_h, x] = dirt[band_h - dip:band_h, x]
    return out


def _dirt(rng):
    return _fill(rng, (117, 79, 42), variance=16, cell=2)


def _stone(rng):
    base = _fill(rng, (128, 128, 130), variance=12, cell=3)
    # a few darker speckled "cracks"
    mask = rng.random((TILE_SIZE, TILE_SIZE)) > 0.93
    base[mask] = (base[mask].astype(np.int16) - 35).clip(0, 255).astype(np.uint8)
    return base


def _cobblestone(rng):
    base = _fill(rng, (115, 115, 120), variance=10, cell=1)
    blob = np.zeros((TILE_SIZE, TILE_SIZE))
    for _ in range(10):
        cx, cy = rng.integers(0, TILE_SIZE, size=2)
        r = rng.integers(3, 7)
        yy, xx = np.ogrid[:TILE_SIZE, :TILE_SIZE]
        blob += ((xx - cx) ** 2 + (yy - cy) ** 2 < r * r) * rng.integers(-30, 30)
    out = np.clip(base.astype(np.int16) + blob[..., None], 0, 255).astype(np.uint8)
    return out


def _planks(rng):
    base = _fill(rng, (184, 140, 82), variance=10, cell=2)
    plank_w = TILE_SIZE // 3
    for i in range(TILE_SIZE):
        if i % plank_w == 0:
            base[:, i:i + 1] = (base[:, i:i + 1].astype(np.int16) - 30).clip(0, 255).astype(np.uint8)
    for row in range(TILE_SIZE):
        if rng.random() < 0.15:
            base[row] = (base[row].astype(np.int16) - 12).clip(0, 255).astype(np.uint8)
    return base


def _log_side(rng):
    base = _fill(rng, (107, 71, 36), variance=10, cell=1)
    for i in range(TILE_SIZE):
        streak = int(8 * math.sin(i * 0.9))
        base[:, i] = (base[:, i].astype(np.int16) + streak).clip(0, 255).astype(np.uint8)
    return base


def _log_top(rng):
    base = _fill(rng, (196, 156, 104), variance=8, cell=1)
    cx, cy = TILE_SIZE / 2, TILE_SIZE / 2
    yy, xx = np.ogrid[:TILE_SIZE, :TILE_SIZE]
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    rings = (np.sin(dist * 1.4) > 0.6)
    base[rings] = (base[rings].astype(np.int16) - 40).clip(0, 255).astype(np.uint8)
    return base


def _leaves(rng):
    return _fill(rng, (54, 107, 33), variance=26, cell=2)


def _brick(rng):
    base = _fill(rng, (150, 70, 50), variance=10, cell=1)
    mortar = (150, 150, 145)
    row_h = TILE_SIZE // 4
    for r in range(0, TILE_SIZE, row_h):
        base[r:r + 2] = mortar
    brick_w = TILE_SIZE // 2
    for ri, r in enumerate(range(0, TILE_SIZE, row_h)):
        offset = 0 if ri % 2 == 0 else brick_w // 2
        for c in range(offset, TILE_SIZE, brick_w):
            base[r:r + row_h, c:c + 2] = mortar
    return base


def _sand(rng):
    return _fill(rng, (222, 205, 154), variance=10, cell=2)


def _water(rng):
    base = _fill(rng, (52, 108, 168), variance=10, cell=2)
    for i in range(TILE_SIZE):
        wave = int(10 * math.sin(i * 0.6))
        base[i] = (base[i].astype(np.int16) + wave).clip(0, 255).astype(np.uint8)
    return base


def _snow(rng):
    return _fill(rng, (235, 240, 245), variance=8, cell=2)


def _glass(rng):
    base = _fill(rng, (198, 232, 232), variance=6, cell=1)
    for i in range(0, TILE_SIZE, 5):
        if i < TILE_SIZE:
            base[max(0, i - 1):i, :] = (255, 255, 255)
    return base


def _gravel(rng):
    base = _fill(rng, (133, 126, 118), variance=22, cell=1)
    return base


def _orange(rng):
    return _fill(rng, (247, 105, 0), variance=12, cell=2)


def _teal(rng):
    return _fill(rng, (0, 138, 147), variance=10, cell=2)


def _charcoal(rng):
    return _fill(rng, (33, 33, 36), variance=8, cell=2)


_PAINTERS = {
    "grass_top": _grass_top,
    "grass_side": _grass_side,
    "dirt": _dirt,
    "stone": _stone,
    "planks": _planks,
    "log_side": _log_side,
    "log_top": _log_top,
    "leaves": _leaves,
    "brick": _brick,
    "sand": _sand,
    "water": _water,
    "cobblestone": _cobblestone,
    "snow": _snow,
    "glass": _glass,
    "gravel": _gravel,
    "orange": _orange,
    "teal": _teal,
    "charcoal": _charcoal,
}


def generate_water_tile(seed=7) -> Image.Image:
    """The water tile alone, standalone (not atlas-packed) so it can have
    its own REPEAT-wrapped texture for a scrolling/animated water surface."""
    rng = np.random.default_rng(seed)
    return Image.fromarray(_water(rng), mode="RGB")


def generate_atlas(seed=7) -> Image.Image:
    rng = np.random.default_rng(seed)
    atlas = np.zeros((ATLAS_ROWS * TILE_SIZE, ATLAS_COLS * TILE_SIZE, 3), dtype=np.uint8)
    for name, tile_idx in TILE_INDEX.items():
        painter = _PAINTERS[name]
        tile = painter(rng)
        row, col = divmod(tile_idx, ATLAS_COLS)
        y0, x0 = row * TILE_SIZE, col * TILE_SIZE
        atlas[y0:y0 + TILE_SIZE, x0:x0 + TILE_SIZE] = tile
    return Image.fromarray(atlas, mode="RGB")


def tile_uv_bounds(tile_name: str):
    """Returns (u0, v0, u1, v1) in the 0..1 atlas for a tile, top-left origin
    (matching glTF's UV convention, so no V-flip is needed)."""
    idx = TILE_INDEX[tile_name]
    row, col = divmod(idx, ATLAS_COLS)
    u0, u1 = col / ATLAS_COLS, (col + 1) / ATLAS_COLS
    v0, v1 = row / ATLAS_ROWS, (row + 1) / ATLAS_ROWS
    return u0, v0, u1, v1


if __name__ == "__main__":
    out = Path(__file__).parent / "out" / "atlas.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img = generate_atlas()
    img = img.resize((img.width * 4, img.height * 4), Image.NEAREST)
    img.save(out)
    print(f"Saved {out} ({img.width}x{img.height})")
