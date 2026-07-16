"""Generates brand plaques identifying each organization -- using their
real logo artwork (see exporter/assets/) the same way a resume or LinkedIn
profile lists a past employer's actual logo, just rendered as a sign board
in the 3D world.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

PLAQUE_W, PLAQUE_H = 512, 256
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_REGULAR = "/System/Library/Fonts/Supplemental/Arial.ttf"
ASSETS_DIR = Path(__file__).parent / "assets"

# real logo screenshots -- each screenshot's "transparent" background is
# actually a baked-in neutral gray grid (screenshots don't carry real
# alpha), cleaned up at load time by _load_logo below
LOGO_ASSETS = {
    "amd": ASSETS_DIR / "amd_logo.png",
    "rit": ASSETS_DIR / "rit_logo.png",
    "siemens": ASSETS_DIR / "siemens_logo.png",
    "nvidia": ASSETS_DIR / "nvidia_logo.png",
}

PLAQUES = {
    "rit": {
        "bg": (255, 255, 255),
        "title": "RIT",
        "title_color": (247, 105, 0),
        "subtitle": "Rochester Institute of Technology",
        "subtitle_color": (40, 40, 40),
    },
    "amd": {
        "bg": (255, 255, 255),
        "title": "AMD",
        "title_color": (0, 0, 0),
        "subtitle": "Advanced Micro Devices",
        "subtitle_color": (60, 60, 60),
    },
    "siemens": {
        "bg": (255, 255, 255),
        "title": "SIEMENS",
        "title_color": (0, 138, 147),
        "subtitle": "Siemens EDA",
        "subtitle_color": (60, 60, 60),
    },
    "nvidia": {
        "bg": (255, 255, 255),
        "title": "NVIDIA",
        "title_color": (118, 185, 0),
        "subtitle": "Starting 2026",
        "subtitle_color": (60, 60, 60),
    },
}


def _centered_text(draw, text, font, y, width, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    draw.text(((width - w) / 2, y), text, font=font, fill=fill)
    return w


def _load_logo(company: str, sat_threshold: int = 15, dark_threshold: int = 80) -> Image.Image:
    """A screenshot's "transparent" background is actually a baked-in
    neutral gray grid (screenshots don't carry real alpha) -- rebuild real
    transparency by keeping any pixel that's either colorful (a brand
    color, e.g. NVIDIA's green or RIT's orange) or near-black (a wordmark,
    e.g. AMD/NVIDIA's), and treating everything else -- neutral, light gray
    -- as background."""
    raw = np.asarray(Image.open(LOGO_ASSETS[company]).convert("RGB"), dtype=np.int16)
    saturation = raw.max(axis=2) - raw.min(axis=2)
    luminance = raw.mean(axis=2)
    keep = (saturation >= sat_threshold) | (luminance < dark_threshold)
    alpha = np.where(keep, 255, 0).astype(np.uint8)
    rgba = np.dstack([raw.astype(np.uint8), alpha])
    return Image.fromarray(rgba, mode="RGBA")


def generate_plaque(company: str) -> Image.Image:
    spec = PLAQUES[company]
    img = Image.new("RGB", (PLAQUE_W, PLAQUE_H), spec["bg"])
    draw = ImageDraw.Draw(img)

    border = 10
    draw.rectangle(
        [border, border, PLAQUE_W - border, PLAQUE_H - border],
        outline=spec["title_color"],
        width=6,
    )

    title_font = ImageFont.truetype(FONT_BOLD, 72)
    subtitle_font = ImageFont.truetype(FONT_REGULAR, 24)

    if company in LOGO_ASSETS:
        logo = _load_logo(company)
        max_w, max_h = PLAQUE_W - 120, 120
        scale = min(max_w / logo.width, max_h / logo.height)
        logo = logo.resize((int(logo.width * scale), int(logo.height * scale)), Image.LANCZOS)
        logo_x = (PLAQUE_W - logo.width) // 2
        logo_y = 45 + (max_h - logo.height) // 2
        img.paste(logo, (logo_x, logo_y), logo)
    else:
        _centered_text(draw, spec["title"], title_font, 78, PLAQUE_W, spec["title_color"])

    _centered_text(draw, spec["subtitle"], subtitle_font, 175, PLAQUE_W, spec["subtitle_color"])

    return img


if __name__ == "__main__":
    out_dir = Path(__file__).parent / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    for company in PLAQUES:
        img = generate_plaque(company)
        path = out_dir / f"plaque_{company}.png"
        img.save(path)
        print(f"Saved {path}")
