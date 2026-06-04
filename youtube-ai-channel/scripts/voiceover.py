"""
voiceover.py
Uses Edge-TTS (Microsoft neural TTS, free, no API key) to convert script text into audio.
Parses generated script markdown files and produces a single audio track with timing data.
"""

import os
import re
import json
import asyncio
import sys
import argparse
from pathlib import Path
from datetime import datetime

import edge_tts

VOICE = "en-US-JennyNeural"
RATE = "+0%"
OUTPUT_DIR = Path("content/audio")


def extract_dialogue(script_text: str) -> list[dict]:
    """Parse script markdown into speakable segments with labels."""
    segments = []
    current_section = "Intro"
    buffer = ""

    def flush_buffer():
        nonlocal buffer
        if buffer.strip():
            text = buffer.strip()
            text = re.sub(r"^\*\*", "", text)
            text = re.sub(r"\*\*$", "", text)
            text = re.sub(r"^-\s*", "", text)
            text = re.sub(r"^>\s*", "", text)
            text = text.strip()
            if len(text) >= 20:
                segments.append({"section": current_section, "text": text})
        buffer = ""

    for line in script_text.split("\n"):
        section_match = re.match(r"^##\s+(.+)", line)
        if section_match:
            flush_buffer()
            current_section = section_match.group(1).strip()
            continue

        stripped = line.strip()
        if not stripped or stripped.startswith("```"):
            flush_buffer()
            continue
        if stripped.startswith("###") or stripped.startswith("["):
            continue
        if re.match(r"^\d+:\d+", stripped):
            continue
        if stripped.startswith("(") and stripped.endswith(")"):
            continue
        if "[ON SCREEN]" in stripped or "[VISUAL]" in stripped:
            continue

        text = re.sub(r"^\*\*", "", stripped)
        text = re.sub(r"\*\*$", "", text)
        text = re.sub(r"^-\s*", "", text)
        text = text.strip()
        if not text:
            flush_buffer()
            continue

        if buffer:
            buffer += " " + text
        else:
            buffer = text

        if len(buffer) > 300:
            flush_buffer()

    flush_buffer()
    return segments


async def generate_segment_audio(segment: dict, index: int) -> dict:
    """Generate audio for one text segment and return timing info."""
    output_file = OUTPUT_DIR / f"seg_{index:03d}.mp3"
    communicate = edge_tts.Communicate(segment["text"], VOICE, rate=RATE)
    duration = 0
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            with open(output_file, "ab") as f:
                f.write(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            duration = chunk.get("duration", 0) / 1e7

    return {
        "index": index,
        "section": segment["section"],
        "text": segment["text"],
        "file": str(output_file),
        "duration": round(duration, 2),
    }


def get_audio_duration(filepath: str) -> float:
    """Get MP3 duration using ffprobe."""
    import subprocess
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", filepath],
        capture_output=True, text=True, timeout=15
    )
    return float(result.stdout.strip() or 0)


async def generate_voiceover(script_path: str, output_path: str | None = None):
    """Full pipeline: parse script → generate audio segments → stitch together."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(script_path) as f:
        script_text = f.read()

    segments = extract_dialogue(script_text)
    if not segments:
        print("No speakable segments found in script.")
        sys.exit(1)

    print(f"Found {len(segments)} segments to narrate")

    tasks = [generate_segment_audio(s, i) for i, s in enumerate(segments)]
    results = await asyncio.gather(*tasks)

    output_path = output_path or str(OUTPUT_DIR / "voiceover.mp3")

    import shutil
    with open(output_path, "wb") as out:
        for r in results:
            dur = get_audio_duration(r["file"])
            r["duration"] = dur
            with open(r["file"], "rb") as seg:
                shutil.copyfileobj(seg, out)

    timing_file = OUTPUT_DIR / "timing.json"
    with open(timing_file, "w") as f:
        json.dump(results, f, indent=2)

    total_duration = sum(r["duration"] for r in results)
    print(f"Voiceover saved: {output_path}")
    print(f"Duration: {total_duration:.1f}s ({int(total_duration//60)}m {int(total_duration%60)}s)")
    print(f"Timing data: {timing_file}")

    return output_path, str(timing_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate voiceover from script")
    parser.add_argument("script", help="Path to generated script markdown file")
    parser.add_argument("--output", help="Output audio path")
    args = parser.parse_args()

    asyncio.run(generate_voiceover(args.script, args.output))
