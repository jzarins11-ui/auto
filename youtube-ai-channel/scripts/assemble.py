"""
assemble.py
Assembles video: background images + voiceover + captions.
"""

import os
import io
import json
import sys
import urllib.request
import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path("content/videos")
WIDTH, HEIGHT = 1920, 1080
FONT_CACHE = {}
_image_cache = []


def get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_paths = [
        "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    if size not in FONT_CACHE:
        FONT_CACHE[size] = ImageFont.load_default()
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    FONT_CACHE[size] = ImageFont.truetype(fp, size)
                    break
                except Exception:
                    continue
    return FONT_CACHE[size]


def hex_to_rgb(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def download_images(keyword: str = "", count: int = 6) -> list[Image.Image]:
    images = []
    urls = []
    if keyword:
        seed = keyword.replace(" ", "-")
        urls = [f"https://picsum.photos/seed/{seed}-{i}/{WIDTH}/{HEIGHT}" for i in range(count)]
    else:
        urls = [f"https://picsum.photos/{WIDTH}/{HEIGHT}?random={i}" for i in range(count)]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(req, timeout=10).read()
            img = Image.open(io.BytesIO(data)).convert("RGB")
            img = img.resize((WIDTH, HEIGHT), Image.LANCZOS)
            images.append(img)
        except Exception as e:
            print(f"  Image download failed: {e}")
    return images


def create_gradient_bg(colors: list[str]) -> Image.Image:
    top_rgb = hex_to_rgb(colors[0])
    bot_rgb = hex_to_rgb(colors[1]) if len(colors) > 1 else top_rgb
    img = Image.new("RGB", (WIDTH, HEIGHT))
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(top_rgb[0] * (1 - ratio) + bot_rgb[0] * ratio)
        g = int(top_rgb[1] * (1 - ratio) + bot_rgb[1] * ratio)
        b = int(top_rgb[2] * (1 - ratio) + bot_rgb[2] * ratio)
        for x in range(WIDTH):
            img.putpixel((x, y), (r, g, b))
    return img


def apply_dark_overlay(img: Image.Image, opacity: float = 0.5) -> Image.Image:
    overlay = Image.new("RGBA", img.size, (0, 0, 0, int(255 * opacity)))
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay)
    return img.convert("RGB")


def ken_burns_crop(img: Image.Image, progress: float, zoom: float = 0.15) -> Image.Image:
    w, h = img.size
    scale = 1.0 + zoom * progress
    new_w, new_h = int(w / scale), int(h / scale)
    offset_x = int((w - new_w) * 0.5 * progress)
    offset_y = int((h - new_h) * 0.3 * progress)
    cropped = img.crop((offset_x, offset_y, offset_x + new_w, offset_y + new_h))
    return cropped.resize((w, h), Image.LANCZOS)


def draw_caption(draw: ImageDraw.Draw, text: str, width: int, height: int):
    font = get_font(52)
    max_w = width - 400
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = font.getbbox(test)
        if (bbox[2] - bbox[0]) <= max_w:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    line_h = 66
    padding = 24
    total_h = len(lines) * line_h
    start_y = height - total_h - 180
    for i, line in enumerate(lines):
        bbox = font.getbbox(line)
        lw = bbox[2] - bbox[0]
        x = (width - lw) // 2
        y = start_y + i * line_h
        pill_x0 = x - padding
        pill_y0 = y - padding // 2
        pill_x1 = x + lw + padding
        pill_y1 = y + line_h + padding // 2
        draw.rounded_rectangle(
            [pill_x0, pill_y0, pill_x1, pill_y1],
            radius=16, fill=(0, 0, 0, 180)
        )
        draw.text((x, y), line, fill=(255, 255, 255), font=font)


def draw_channel_name(draw: ImageDraw.Draw, name: str, width: int):
    font = get_font(40)
    bbox = font.getbbox(name)
    cw = bbox[2] - bbox[0]
    x = (width - cw) // 2
    pill_x0 = x - 20
    pill_x1 = x + cw + 20
    draw.rounded_rectangle([pill_x0, 20, pill_x1, 70], radius=12, fill=(255, 215, 0, 200))
    draw.text((x, 26), name, fill=(0, 0, 0), font=font)


def render_caption_frame(text: str, channel_name: str = "") -> np.ndarray:
    global _image_cache
    img = _image_cache[0] if _image_cache else create_gradient_bg(["#1a1a2e", "#16213e"])
    img = apply_dark_overlay(img.copy(), 0.45)
    draw = ImageDraw.Draw(img)
    if channel_name:
        draw_channel_name(draw, channel_name, WIDTH)
    if text:
        draw_caption(draw, text, WIDTH, HEIGHT)
    return np.array(img)


def render_bg_frame(t: float, images: list, seg_starts: list, seg_texts: list,
                    seg_durations: list, total_duration: float,
                    channel_name: str, image_duration: float) -> np.ndarray:
    if not images:
        img = create_gradient_bg(["#1a1a2e", "#16213e"])
        return np.array(apply_dark_overlay(img, 0.45))

    img_idx = min(int(t / image_duration), len(images) - 1)
    img = images[img_idx]
    progress_in_image = (t % image_duration) / image_duration
    frame = ken_burns_crop(img, progress_in_image)
    frame = apply_dark_overlay(frame, 0.45)
    draw = ImageDraw.Draw(frame)
    if channel_name:
        draw_channel_name(draw, channel_name, WIDTH)

    for i, start in enumerate(seg_starts):
        end = start + seg_durations[i]
        if start <= t < end:
            draw_caption(draw, seg_texts[i], WIDTH, HEIGHT)
            break

    return np.array(frame)


def assemble_video(
    audio_path: str,
    output_path: str,
    timing_path: str | None = None,
    colors: list[str] | None = None,
    channel_name: str = "",
    keyword: str = "",
):
    global _image_cache
    from moviepy import AudioFileClip, VideoClip

    colors = colors or ["#1a1a2e", "#16213e"]

    audio = AudioFileClip(audio_path)
    total_duration = audio.duration

    seg_starts = []
    seg_texts = []
    seg_durations = []

    if timing_path and os.path.exists(timing_path):
        with open(timing_path) as f:
            segments = json.load(f)
        current_time = 0.0
        for seg in segments:
            dur = seg["duration"]
            if dur > 1.0:
                seg_starts.append(current_time)
                seg_texts.append(seg["text"])
                seg_durations.append(dur)
            current_time += dur

    print("Downloading background images...")
    images = download_images(keyword, count=6)
    if not images:
        print("No images downloaded, using gradient background")
        images = [create_gradient_bg(colors)]
    _image_cache = images

    image_duration = total_duration / max(len(images), 1)

    bg_clip = VideoClip(
        lambda t: render_bg_frame(
            t, images, seg_starts, seg_texts, seg_durations,
            total_duration, channel_name, image_duration
        ),
        duration=total_duration,
    ).with_fps(15)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    final = bg_clip.with_audio(audio)

    final.write_videofile(
        str(output_path),
        codec="libx264",
        audio_codec="aac",
        preset="fast",
        bitrate="5000k",
        threads=2,
    )

    print(f"Video saved: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assemble video from audio and captions")
    parser.add_argument("--audio", required=True, help="Path to voiceover audio")
    parser.add_argument("--output", default=str(OUTPUT_DIR / "final.mp4"), help="Output video path")
    parser.add_argument("--timing", help="Path to timing.json for captions")
    parser.add_argument("--channel", default="", help="Channel name overlay")
    parser.add_argument("--colors", nargs=2, default=["#1a1a2e", "#16213e"], help="Gradient colors")
    parser.add_argument("--keyword", default="", help="Topic keyword for image search")
    args = parser.parse_args()

    assemble_video(args.audio, args.output, args.timing, args.colors, args.channel, args.keyword)
