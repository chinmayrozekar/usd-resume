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

# real logo screenshots -- each paired with the thresholding strategy that
# recovers real alpha from the baked-in checkerboard "transparency" a
# screenshot actually captures (see _load_luminance_logo / _load_saturation_logo)
LOGO_ASSETS = {
    "amd": (ASSETS_DIR / "amd_logo.png", "luminance"),  # black-on-white mark
    "rit": (ASSETS_DIR / "rit_logo.png", "saturation"),  # colored wordmark
    "siemens": (ASSETS_DIR / "siemens_logo.png", "saturation"),  # colored wordmark
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
}


def _centered_text(draw, text, font, y, width, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    draw.text(((width - w) / 2, y), text, font=font, fill=fill)
    return w


def _load_luminance_logo(path: Path, threshold: int = 140) -> Image.Image:
    """For a black-on-white mark (AMD): a screenshot's "transparent"
    background is actually a checkerboard baked into ordinary opaque pixels
    -- rebuild real transparency by thresholding on darkness, since the
    checkerboard is light gray/white and the mark itself is near-black."""
    raw = Image.open(path).convert("RGB")
    gray = raw.convert("L")
    alpha = gray.point(lambda p: 255 if p < threshold else 0)
    logo = Image.new("RGBA", raw.size, (0, 0, 0, 255))
    logo.putalpha(alpha)
    return logo


def _load_saturation_logo(path: Path, sat_threshold: int = 18) -> Image.Image:
    """For a colored wordmark (RIT, Siemens): darkness alone can't separate
    mark from checkerboard since the light checker square is nearly as
    bright as some logo colors -- but the checkerboard is neutral gray
    (R==G==B) while the logo color is saturated, so threshold on that
    instead. Same underlying problem as _load_luminance_logo, different
    signal because the mark itself isn't black/white here."""
    raw = np.asarray(Image.open(path).convert("RGB"), dtype=np.int16)
    saturation = raw.max(axis=2) - raw.min(axis=2)
    alpha = np.where(saturation >= sat_threshold, 255, 0).astype(np.uint8)
    rgba = np.dstack([raw.astype(np.uint8), alpha])
    return Image.fromarray(rgba, mode="RGBA")


def _load_logo(company: str) -> Image.Image:
    path, mode = LOGO_ASSETS[company]
    if mode == "luminance":
        return _load_luminance_logo(path)
    return _load_saturation_logo(path)


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
        target_w = PLAQUE_W - 120
        scale = target_w / logo.width
        logo = logo.resize((target_w, int(logo.height * scale)), Image.LANCZOS)
        logo_x = (PLAQUE_W - logo.width) // 2
        logo_y = 55 + (100 - logo.height) // 2
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
