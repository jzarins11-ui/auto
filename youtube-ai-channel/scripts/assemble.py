"""
assemble.py
Assembles video: background images + voiceover + captions + script-aware visuals.
"""

import os
import io
import json
import re
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
SECTION_CARD_DURATION = 2.5
CROSSFADE_TIME = 0.5


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


def download_images(keyword: str = "", count: int = 8) -> list[Image.Image]:
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


def blend_images(img1: Image.Image, img2: Image.Image, alpha: float) -> Image.Image:
    return Image.blend(img1, img2, alpha)


def ken_burns_crop(img: Image.Image, progress: float, zoom: float = 0.12) -> Image.Image:
    w, h = img.size
    scale = 1.0 + zoom * progress
    new_w, new_h = int(w / scale), int(h / scale)
    offset_x = int((w - new_w) * 0.5 * progress)
    offset_y = int((h - new_h) * 0.3 * progress)
    cropped = img.crop((offset_x, offset_y, offset_x + new_w, offset_y + new_h))
    return cropped.resize((w, h), Image.LANCZOS)


def wrap_text(text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = font.getbbox(test)
        if (bbox[2] - bbox[0]) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_caption(draw: ImageDraw.Draw, text: str, width: int, height: int, font_size: int = 52, accent: bool = False):
    font = get_font(font_size)
    max_w = width - 400
    lines = wrap_text(text, font, max_w)
    line_h = int(font_size * 1.27)
    padding_x = 28
    padding_y = 14
    total_h = len(lines) * line_h
    start_y = height - total_h - 120
    accent_fill = (numpy_uint8(255), numpy_uint8(215), numpy_uint8(0), numpy_uint8(180)) if accent else None
    for i, line in enumerate(lines):
        bbox = font.getbbox(line)
        lw = bbox[2] - bbox[0]
        x = (width - lw) // 2
        y = start_y + i * line_h
        px0 = x - padding_x
        py0 = y - padding_y // 2
        px1 = x + lw + padding_x
        py1 = y + line_h + padding_y // 2
        fill = accent_fill if accent_fill else (0, 0, 0, 160)
        draw.rounded_rectangle([px0, py0, px1, py1], radius=16, fill=fill)
        draw.text((x, y), line, fill=(255, 255, 255), font=font)


def draw_channel_name(draw: ImageDraw.Draw, name: str, width: int):
    font = get_font(40)
    bbox = font.getbbox(name)
    cw = bbox[2] - bbox[0]
    x = (width - cw) // 2
    draw.rounded_rectangle([x - 20, 20, x + cw + 20, 70], radius=12, fill=(255, 215, 0, 200))
    draw.text((x, 26), name, fill=(0, 0, 0), font=font)


def draw_section_card(draw: ImageDraw.Draw, section: str, index: int, total: int, width: int, height: int):
    title_font = get_font(86)
    idx_font = get_font(32)
    lines = wrap_text(section, title_font, width - 200)
    total_h = len(lines) * 100
    start_y = (height - total_h) // 2 - 40
    draw.rounded_rectangle(
        [width//2 - 500, start_y - 60, width//2 + 500, start_y + total_h + 60],
        radius=30, fill=(0, 0, 0, 160)
    )
    for i, line in enumerate(lines):
        bbox = title_font.getbbox(line)
        lw = bbox[2] - bbox[0]
        draw.text(((width - lw) // 2, start_y + i * 100), line, fill=(255, 255, 255), font=title_font)
    step_text = f"Part {index} of {total}"
    bbox = idx_font.getbbox(step_text)
    draw.text(
        ((width - (bbox[2] - bbox[0])) // 2, start_y + total_h + 20),
        step_text, fill=(255, 215, 0), font=idx_font
    )


def draw_hook_text(draw: ImageDraw.Draw, text: str, width: int, height: int):
    font = get_font(96)
    lines = wrap_text(text, font, width - 200)
    total_h = len(lines) * 115
    start_y = (height - total_h) // 2
    for i, line in enumerate(lines):
        bbox = font.getbbox(line)
        lw = bbox[2] - bbox[0]
        x = (width - lw) // 2
        y = start_y + i * 115
        draw.text((x + 4, y + 4), line, fill=(0, 0, 0, 120), font=font)
        draw.text((x, y), line, fill=(255, 255, 255), font=font)


def draw_recap_bullets(draw: ImageDraw.Draw, seg_texts: list[str], progress: float, width: int, height: int):
    font = get_font(50)
    bullet_color = (255, 215, 0)
    text_color = (255, 255, 255)
    visible = max(1, int(progress * len(seg_texts)))
    start_y = (height - len(seg_texts) * 80) // 2
    for i in range(visible):
        text = seg_texts[i]
        display = text[3:] if text.startswith("- ") else text
        display = re.sub(r"^\*\*(.*?)\*\*", r"\1", display)
        y = start_y + i * 80
        draw.text((width // 2 - 300, y), ">", fill=bullet_color, font=font)
        bbox = font.getbbox(display)
        lw = bbox[2] - bbox[0]
        draw.text((width // 2 - 280, y), display, fill=text_color, font=font)


def parse_script(script_path: str) -> dict:
    """Parse script markdown into sections and on-screen cues."""
    sections = []
    onscreen_cues = []
    current_section = "HOOK"
    current_section_line = 0

    with open(script_path) as f:
        lines = f.readlines()

    line_idx = 0
    for line in lines:
        line_idx += 1
        stripped = line.strip()
        section_match = re.match(r"^##\s+(.+)", stripped)
        if section_match:
            current_section = section_match.group(1).strip()
            current_section_line = line_idx
            sections.append({"name": current_section, "line": line_idx})
        onscreen_match = re.findall(r"\[ON SCREEN\](.*?)(?:\[|$)", stripped)
        for m in onscreen_match:
            onscreen_cues.append({
                "text": m.strip(),
                "section": current_section,
                "line": line_idx,
            })

    return {"sections": sections, "cues": onscreen_cues}


def classify_section(name: str) -> str:
    upper = name.upper().strip()
    if upper == "HOOK":
        return "hook"
    if upper in ("INTRO", "INTRODUCTION"):
        return "intro"
    if upper.startswith("RECAP") or "SUMMARY" in upper or "KEY TAKEAWAYS" in upper:
        return "recap"
    if "CALL TO ACTION" in upper or upper == "CTA" or "OUTRO" in upper:
        return "cta"
    return "content"


def build_visual_timeline(timing_segments: list) -> list:
    """Merge timing segments with section info to build visual events."""
    events = []
    prev_section = ""
    current_time = 0.0

    for seg in timing_segments:
        section_name = seg.get("section", "").strip()
        dur = seg.get("duration", 0)
        text = seg.get("text", "")

        if section_name != prev_section and prev_section != "":
            vtype = classify_section(section_name)
            if vtype == "content":
                events.append({
                    "type": "section_card",
                    "start": current_time,
                    "duration": SECTION_CARD_DURATION,
                    "text": section_name,
                    "section": section_name,
                })

        events.append({
            "type": "dialogue",
            "start": current_time,
            "duration": dur,
            "text": text,
            "section": section_name or seg.get("section", ""),
        })

        current_time += dur
        prev_section = section_name

    return events


def get_active_event(events: list, t: float) -> dict | None:
    for ev in events:
        if ev["start"] <= t < ev["start"] + ev["duration"]:
            return ev
    return None


def numpy_uint8(v):
    return v


def render_frame(t: float, images: list, events: list, total_duration: float,
                 channel_name: str, image_duration: float, section_count: int) -> np.ndarray:
    if not images:
        img = create_gradient_bg(["#1a1a2e", "#16213e"])
        return np.array(apply_dark_overlay(img, 0.45))

    ev = get_active_event(events, t)
    ev_type = ev["type"] if ev else "dialogue"
    ev_text = ev.get("text", "") if ev else ""
    ev_section = ev.get("section", "") if ev else ""

    raw_idx = t / image_duration
    img_idx = min(int(raw_idx), len(images) - 1)
    next_img_idx = min(img_idx + 1, len(images) - 1)
    progress_in_img = (t % image_duration) / image_duration

    seg = min(int(progress_in_img * 10) / 10, 1.0)
    if next_img_idx > img_idx and progress_in_img > (1.0 - CROSSFADE_TIME / image_duration):
        fade_progress = (progress_in_img - (1.0 - CROSSFADE_TIME / image_duration)) / (CROSSFADE_TIME / image_duration)
        frame1 = ken_burns_crop(images[img_idx], 1.0)
        frame2 = ken_burns_crop(images[next_img_idx], 0.0)
        frame = blend_images(frame1, frame2, min(fade_progress, 1.0))
    else:
        frame = ken_burns_crop(images[img_idx], progress_in_img)

    frame = apply_dark_overlay(frame, 0.45)
    draw = ImageDraw.Draw(frame)

    if channel_name:
        draw_channel_name(draw, channel_name, WIDTH)

    if ev_type == "section_card":
        elapsed = t - ev["start"]
        fade = min(elapsed / 0.3, 1.0)
        if fade < 1.0:
            alpha = int(255 * fade)
            overlay = Image.new("RGBA", frame.size, (0, 0, 0, alpha))
            frame_rgba = frame.convert("RGBA")
            frame_rgba = Image.alpha_composite(frame_rgba, overlay)
            frame = frame_rgba.convert("RGB")
            draw = ImageDraw.Draw(frame)
        draw_section_card(draw, ev_text, img_idx + 1, section_count, WIDTH, HEIGHT)

    elif ev_type == "hook":
        over = Image.new("RGBA", frame.size, (0, 0, 0, 80))
        frame_rgba = frame.convert("RGBA")
        frame_rgba = Image.alpha_composite(frame_rgba, over)
        frame = frame_rgba.convert("RGB")
        draw = ImageDraw.Draw(frame)
        draw_hook_text(draw, ev_text, WIDTH, HEIGHT)

    elif ev_type == "recap":
        clip_events = [e for e in events if e.get("section") == ev_section]
        clip_duration = sum(e["duration"] for e in clip_events) if clip_events else 1
        local_t = t - clip_events[0]["start"] if clip_events else 0
        progress = local_t / clip_duration if clip_duration > 0 else 0
        recap_texts = [e["text"] for e in clip_events if e["type"] == "dialogue"]
        draw_recap_bullets(draw, recap_texts, progress, WIDTH, HEIGHT)

    elif ev_type == "cta":
        over = Image.new("RGBA", frame.size, (0, 0, 0, 60))
        frame_rgba = frame.convert("RGBA")
        frame_rgba = Image.alpha_composite(frame_rgba, over)
        frame = frame_rgba.convert("RGB")
        draw = ImageDraw.Draw(frame)
        if ev_text:
            draw_caption(draw, ev_text, WIDTH, HEIGHT, font_size=56, accent=True)

    elif ev_type == "dialogue":
        if ev_text:
            draw_caption(draw, ev_text, WIDTH, HEIGHT)

    return np.array(frame)


def assemble_video(
    audio_path: str,
    output_path: str,
    timing_path: str | None = None,
    script_path: str | None = None,
    colors: list[str] | None = None,
    channel_name: str = "",
    keyword: str = "",
):
    global _image_cache
    from moviepy import AudioFileClip, VideoClip

    colors = colors or ["#1a1a2e", "#16213e"]

    audio = AudioFileClip(audio_path)
    total_duration = audio.duration

    timing_segments = []
    if timing_path and os.path.exists(timing_path):
        with open(timing_path) as f:
            timing_segments = json.load(f)

    script_data = None
    if script_path and os.path.exists(script_path):
        script_data = parse_script(script_path)
        print(f"Parsed script: {len(script_data['sections'])} sections, {len(script_data['cues'])} on-screen cues")
    else:
        print("No script provided, using basic caption mode")

    events = build_visual_timeline(timing_segments)
    section_names = list(dict.fromkeys(s.get("section", "") for s in timing_segments if s.get("section")))
    section_count = max(len(section_names), 1)
    print(f"Built timeline: {len(events)} events across {section_count} sections")

    print("Downloading background images...")
    images = download_images(keyword, count=8)
    if not images:
        print("No images downloaded, using gradient background")
        images = [create_gradient_bg(colors)]
    _image_cache = images

    image_duration = total_duration / max(len(images), 1)

    bg_clip = VideoClip(
        lambda t: render_frame(
            t, images, events, total_duration, channel_name, image_duration, section_count
        ),
        duration=total_duration,
    ).with_fps(30)

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
    parser.add_argument("--script", help="Path to script markdown for section-aware rendering")
    parser.add_argument("--channel", default="", help="Channel name overlay")
    parser.add_argument("--colors", nargs=2, default=["#1a1a2e", "#16213e"], help="Gradient colors")
    parser.add_argument("--keyword", default="", help="Topic keyword for image search")
    args = parser.parse_args()

    assemble_video(args.audio, args.output, args.timing, args.script, args.colors, args.channel, args.keyword)
