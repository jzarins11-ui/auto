"""
full_automation.py
End-to-end pipeline: trend analysis → content calendar → script → voiceover → thumbnail → video → upload.

Usage:
  python scripts/full_automation.py
  python scripts/full_automation.py --topic "AI tools 2026" --upload
  python scripts/full_automation.py --script-only --output my-video.mp4
"""

import os
import sys
import json
import asyncio
import subprocess
import argparse
from pathlib import Path
from datetime import datetime


def load_config():
    with open("config/channel_config.json") as f:
        return json.load(f)


def run_step(step_name: str, *args: str) -> bool:
    print(f"\n{'='*60}")
    print(f"STEP: {step_name}")
    print(f"{'='*60}")
    result = subprocess.run(args, capture_output=False)
    if result.returncode != 0:
        print(f"[FAIL] {step_name} — exit code {result.returncode}")
        return False
    print(f"[OK] {step_name}")
    return True


def find_latest_script() -> str | None:
    scripts_dir = Path("content/scripts")
    if not scripts_dir.exists():
        return None
    md_files = sorted(scripts_dir.glob("*_script.md"), key=os.path.getmtime, reverse=True)
    return str(md_files[0]) if md_files else None


def find_latest_meta() -> str | None:
    scripts_dir = Path("content/scripts")
    if not scripts_dir.exists():
        return None
    meta_files = sorted(scripts_dir.glob("*_meta.md"), key=os.path.getmtime, reverse=True)
    return str(meta_files[0]) if meta_files else None


def get_script_title(script_path: str) -> str:
    with open(script_path) as f:
        for line in f:
            if line.startswith("# ") and len(line) > 3:
                return line.strip("# ").strip()
    return "Untitled Video"


def main():
    parser = argparse.ArgumentParser(description="Full YouTube automation pipeline")
    parser.add_argument("--topic", help="Video topic (skip trend/calendar steps if provided)")
    parser.add_argument("--video-type", default="tutorial", choices=["tutorial", "comparison", "case-study", "money-making", "news"])
    parser.add_argument("--keyword", help="Primary SEO keyword")
    parser.add_argument("--affiliate", default="", help="Affiliate product to feature")
    parser.add_argument("--upload", action="store_true", help="Upload the finished video to YouTube")
    parser.add_argument("--privacy", choices=["public", "unlisted", "private"], default="unlisted", help="Upload privacy (default: unlisted)")
    parser.add_argument("--output", help="Output video file path")
    parser.add_argument("--script-file", help="Use existing script file instead of generating new one")
    parser.add_argument("--skip-trends", action="store_true", help="Skip trend analysis")
    parser.add_argument("--skip-calendar", action="store_true", help="Skip calendar generation")
    args = parser.parse_args()

    config = load_config()
    channel_name = config.get("channel_name", "My Channel")
    colors = config.get("video_colors", ["#1a1a2e", "#16213e"])

    if args.topic and not args.keyword:
        args.keyword = args.topic

    if not args.skip_trends and not args.topic:
        run_step("Fetch trends",
            sys.executable, "scripts/fetch_top_videos.py"
        )
        run_step("Analyze trends",
            sys.executable, "scripts/analyze_trends.py"
        )

    if not args.skip_calendar and not args.topic:
        run_step("Generate calendar",
            sys.executable, "scripts/generate_content_calendar.py"
        )

    if args.script_file:
        script_path = args.script_file
        print(f"Using existing script: {script_path}")
    else:
        script_args = ["scripts/generate_video_script.py"]
        if args.topic:
            script_args.extend(["--topic", args.topic])
        if args.video_type:
            script_args.extend(["--type", args.video_type])
        if args.keyword:
            script_args.extend(["--keyword", args.keyword])
        if args.affiliate:
            script_args.extend(["--affiliate", args.affiliate])
        if not run_step("Generate script", sys.executable, *script_args):
            sys.exit(1)
        script_path = find_latest_script()
        if not script_path:
            print("No script file found after generation.")
            sys.exit(1)

    title = get_script_title(script_path)
    print(f"\nTitle: {title}")

    meta_path = find_latest_meta()

    if not run_step("Voiceover",
        sys.executable, "scripts/voiceover.py", script_path,
        "--output", "content/audio/voiceover.mp3"
    ):
        sys.exit(1)

    if not run_step("Thumbnail",
        sys.executable, "scripts/thumbnails.py",
        "--title", title,
        "--output", "content/thumbnails/thumbnail.jpg",
        "--channel", channel_name,
        "--colors", colors[0], colors[1] if len(colors) > 1 else colors[0]
    ):
        sys.exit(1)

    output_video = args.output or "content/videos/final.mp4"
    if not run_step("Assemble video",
        sys.executable, "scripts/assemble.py",
        "--audio", "content/audio/voiceover.mp3",
        "--output", output_video,
        "--timing", "content/audio/timing.json",
        "--channel", channel_name,
        "--colors", colors[0], colors[1] if len(colors) > 1 else colors[0]
    ):
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"VIDEO READY: {output_video}")
    print(f"Title: {title}")
    print(f"Thumbnail: content/thumbnails/thumbnail.jpg")
    print(f"{'='*60}")

    if args.upload:
        upload_args = [
            sys.executable, "scripts/upload_to_youtube.py",
            output_video,
            "--title", title,
            "--thumbnail", "content/thumbnails/thumbnail.jpg",
            "--privacy", args.privacy,
        ]
        if meta_path:
            upload_args.extend(["--meta-file", meta_path])
        if not run_step("Upload to YouTube", *upload_args):
            sys.exit(1)
        print("\n[OK] Full pipeline complete — video uploaded to YouTube!")


if __name__ == "__main__":
    main()
