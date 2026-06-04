"""
assemble.py
Assembles the final YouTube video: background + voiceover + captions.
Uses MoviePy for video composition and Pillow for text frames.
"""

import os
import json
import sys
import subprocess
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path("content/videos")
WIDTH, HEIGHT = 1920, 1080


def hex_to_rgb(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def create_bg_frame(
    width: int,
    height: int,
    colors: list[str],
    channel_name: str = "",
    text: str = "",
) -> Image.Image:
    top_rgb = hex_to_rgb(colors[0])
    bot_rgb = hex_to_rgb(colors[1]) if len(colors) > 1 else top_rgb
    img = Image.new("RGB", (width, height))
    for y in range(height):
        ratio = y / height
        r = int(top_rgb[0] * (1 - ratio) + bot_rgb[0] * ratio)
        g = int(top_rgb[1] * (1 - ratio) + bot_rgb[1] * ratio)
        b = int(top_rgb[2] * (1 - ratio) + bot_rgb[2] * ratio)
        for x in range(width):
            img.putpixel((x, y), (r, g, b))
    draw = ImageDraw.Draw(img)

    if channel_name:
        font_paths = [
            "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
        font = None
        for fp in font_paths:
            if os.path.exists(fp):
                font = ImageFont.truetype(fp, 48)
                break
        if not font:
            font = ImageFont.load_default()
        bbox = font.getbbox(channel_name)
        cw = bbox[2] - bbox[0]
        draw.text(((width - cw) // 2, 30), channel_name, fill=(255, 215, 0), font=font)

    if text:
        font_paths = [
            "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
        font = None
        for fp in font_paths:
            if os.path.exists(fp):
                font = ImageFont.truetype(fp, 56)
                break
        if not font:
            font = ImageFont.load_default()
        max_w = width - 200
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

        total_h = len(lines) * 70
        start_y = (height - total_h) // 2 + 100
        for i, line in enumerate(lines):
            bbox = font.getbbox(line)
            lw = bbox[2] - bbox[0]
            x = (width - lw) // 2
            y = start_y + i * 70
            draw.text((x + 2, y + 2), line, fill=(0, 0, 0, 180), font=font)
            draw.text((x, y), line, fill=(255, 255, 255), font=font)

    return img


def create_bg_video(
    audio_path: str,
    output_path: str,
    colors: list[str],
    channel_name: str = "",
    caption_frames: list[dict] | None = None,
):
    import numpy as np
    from moviepy import (
        VideoClip, AudioFileClip, ImageClip, CompositeVideoClip, TextClip, concatenate_videoclips
    )

    audio = AudioFileClip(audio_path)
    duration = audio.duration

    if caption_frames:
        clips = []
        for i, frame in enumerate(caption_frames):
            bg = create_bg_frame(WIDTH, HEIGHT, colors, channel_name, frame["text"])
            bg_path = OUTPUT_DIR / f"frame_{i:04d}.png"
            bg.save(bg_path)
            clip = ImageClip(str(bg_path)).with_duration(frame["duration"])
            clips.append(clip)

        if not clips:
            bg = create_bg_frame(WIDTH, HEIGHT, colors, channel_name)
            bg_path = OUTPUT_DIR / "frame_0000.png"
            bg.save(bg_path)
            clips = [ImageClip(str(bg_path)).with_duration(duration)]

        video = concatenate_videoclips(clips)
    else:
        bg = create_bg_frame(WIDTH, HEIGHT, colors, channel_name)
        bg_path = OUTPUT_DIR / "frame_0000.png"
        bg.save(bg_path)
        video = ImageClip(str(bg_path)).with_duration(duration)

    video = video.with_audio(audio)
    video = video.with_fps(30)

    video.write_videofile(
        str(output_path),
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        bitrate="4000k",
        threads=2,
    )

    print(f"Video saved: {output_path}")
    return output_path


def assemble_video(
    audio_path: str,
    output_path: str,
    timing_path: str | None = None,
    colors: list[str] | None = None,
    channel_name: str = "",
):
    colors = colors or ["#1a1a2e", "#16213e"]

    caption_frames = None
    if timing_path and os.path.exists(timing_path):
        with open(timing_path) as f:
            segments = json.load(f)
        caption_frames = [
            {"text": seg["text"], "duration": seg["duration"]}
            for seg in segments if seg["duration"] > 1.0
        ]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    create_bg_video(audio_path, output_path, colors, channel_name, caption_frames)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assemble video from audio and captions")
    parser.add_argument("--audio", required=True, help="Path to voiceover audio")
    parser.add_argument("--output", default=str(OUTPUT_DIR / "final.mp4"), help="Output video path")
    parser.add_argument("--timing", help="Path to timing.json for captions")
    parser.add_argument("--channel", default="", help="Channel name overlay")
    parser.add_argument("--colors", nargs=2, default=["#1a1a2e", "#16213e"], help="Gradient colors")
    args = parser.parse_args()

    assemble_video(args.audio, args.output, args.timing, args.colors, args.channel)
