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

    for line in script_text.split("\n"):
        section_match = re.match(r"^##\s+(.+)", line)
        if section_match:
            current_section = section_match.group(1).strip()

        on_screen = re.match(r"^-?\s*\[ON SCREEN\]", line)
        spoken = re.match(r"^-?\s*(.+)$", line)

        stripped = line.strip()
        if not stripped or stripped.startswith("```") or stripped.startswith("["):
            continue
        if on_screen:
            continue
        if stripped.startswith("###"):
            continue
        if re.match(r"^\d+:\d+", stripped):
            continue

        text = re.sub(r"^\*\*", "", stripped)
        text = re.sub(r"\*\*$", "", text)
        text = re.sub(r"^-\s*", "", text)
        text = text.strip()
        if len(text) < 10 or text.startswith("(") and text.endswith(")"):
            continue

        segments.append({"section": current_section, "text": text})

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

    concat_list = OUTPUT_DIR / "concat.txt"
    with open(concat_list, "w") as f:
        for r in results:
            dur = get_audio_duration(r["file"])
            r["duration"] = dur
            rel_path = os.path.relpath(r["file"], OUTPUT_DIR)
            f.write(f"file '{rel_path}'\n")

    output_path = output_path or str(OUTPUT_DIR / "voiceover.mp3")
    import subprocess
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", str(concat_list), output_path],
        check=True, timeout=120
    )

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
