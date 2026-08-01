#!/usr/bin/env python3
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ICONSET = ROOT / "assets" / "AppIcon.iconset"
ICNS = ROOT / "assets" / "AppIcon.icns"
SIZES = [16, 32, 64, 128, 256, 512, 1024]


def make_base_icon(size):
    image = Image.new("RGBA", (size, size), (0, 0, 0, 255))
    draw = ImageDraw.Draw(image)
    font_size = round(size * 0.47)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()

    text = "RJ"
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (size - (bbox[2] - bbox[0])) / 2
    y = (size - (bbox[3] - bbox[1])) / 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
    return image


def main():
    ICONSET.mkdir(parents=True, exist_ok=True)
    for size in SIZES:
        image = make_base_icon(size)
        if size <= 512:
            image.save(ICONSET / f"icon_{size}x{size}.png")
        if size >= 32:
            image.save(ICONSET / f"icon_{size // 2}x{size // 2}@2x.png")
    if ICNS.exists():
        ICNS.unlink()


if __name__ == "__main__":
    main()
