"""
thumbnails.py
Generates YouTube thumbnails using Pillow (no API calls).
Produces gradient-background images with centered title text.
"""

import os
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUTPUT_DIR = Path("content/thumbnails")
WIDTH, HEIGHT = 1280, 720


def hex_to_rgb(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def create_gradient(width: int, height: int, colors: list[str]) -> Image.Image:
    """Create a vertical gradient image from top to bottom color(s)."""
    base = Image.new("RGB", (width, height))
    top_rgb = hex_to_rgb(colors[0])
    bot_rgb = hex_to_rgb(colors[1]) if len(colors) > 1 else top_rgb

    for y in range(height):
        ratio = y / height
        r = int(top_rgb[0] * (1 - ratio) + bot_rgb[0] * ratio)
        g = int(top_rgb[1] * (1 - ratio) + bot_rgb[1] * ratio)
        b = int(top_rgb[2] * (1 - ratio) + bot_rgb[2] * ratio)
        for x in range(width):
            base.putpixel((x, y), (r, g, b))
    return base


def find_best_font(size: int) -> ImageFont.FreeTypeFont:
    """Try to load a bold font from common OS locations."""
    font_candidates = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in font_candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Split text into lines that fit within max_width."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = font.getbbox(test)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def generate_thumbnail(
    title: str,
    output_path: str,
    channel_name: str = "",
    gradient_colors: list[str] | None = None,
):
    colors = gradient_colors or ["#1a1a2e", "#16213e"]
    img = create_gradient(WIDTH, HEIGHT, colors)
    draw = ImageDraw.Draw(img)

    font_size = 72
    font = find_best_font(font_size)
    max_text_width = WIDTH - 160

    lines = wrap_text(title, font, max_text_width)
    if len(lines) > 4:
        font = find_best_font(56)
        lines = wrap_text(title, font, max_text_width)

    total_text_height = len(lines) * (font_size + 10)
    start_y = (HEIGHT - total_text_height) // 2

    for i, line in enumerate(lines):
        bbox = font.getbbox(line)
        text_w = bbox[2] - bbox[0]
        x = (WIDTH - text_w) // 2
        y = start_y + i * (font_size + 10)

        draw.text((x + 3, y + 3), line, fill=(0, 0, 0, 128), font=font)
        draw.text((x, y), line, fill=(255, 255, 255), font=font)

    if channel_name:
        bottom_font = find_best_font(36)
        bbox = bottom_font.getbbox(channel_name)
        cw = bbox[2] - bbox[0]
        cx = (WIDTH - cw) // 2
        cy = HEIGHT - 80
        draw.text((cx + 2, cy + 2), channel_name, fill=(0, 0, 0, 128), font=bottom_font)
        draw.text((cx, cy), channel_name, fill=(255, 215, 0), font=bottom_font)

    img.save(output_path, "JPEG", quality=95)
    print(f"Thumbnail saved: {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate YouTube thumbnail")
    parser.add_argument("--title", required=True, help="Video title")
    parser.add_argument("--output", default=str(OUTPUT_DIR / "thumbnail.jpg"), help="Output image path")
    parser.add_argument("--channel", default="", help="Channel name overlay")
    parser.add_argument("--colors", nargs=2, default=["#1a1a2e", "#16213e"], help="Gradient colors (top bottom)")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    generate_thumbnail(args.title, args.output, args.channel, args.colors)
