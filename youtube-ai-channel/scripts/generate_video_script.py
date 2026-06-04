"""
generate_video_script.py
Generates a full YouTube video script using an LLM (DeepSeek/Claude).
"""

import os
import json
import sys
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.llm import chat


def load_config() -> dict:
    with open("config/channel_config.json") as f:
        return json.load(f)


def slugify(text: str) -> str:
    import re
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:60]


def build_prompt(config: dict, topic: str, video_type: str,
                  keyword: str, affiliate: str) -> str:

    type_guidance = {
        "tutorial": "Step-by-step tutorial. Show exactly how to do something. Viewers want to follow along.",
        "money-making": "Income/side-hustle focused. Lead with earnings proof or potential. Inspire action.",
        "comparison": "Objective comparison. Use a scoring table. End with a clear winner + use case breakdown.",
        "case-study":  "Real story format. Problem -> solution -> results. Be specific with numbers.",
        "news":        "News + your take. Explain what it means for the viewer. Fast-paced, keep it punchy.",
    }.get(video_type, "General informational video.")

    return f"""You are a YouTuber making a video for your channel "{config['channel_name']}".
Niche: {config['niche']}
Your audience: {config['target_audience']}

TOPIC: {topic}
TYPE: {video_type} - {type_guidance}
KEYWORD: {keyword}
AFFILIATE: {affiliate}

Write the script as if you're talking to a friend — natural, conversational, energetic. No corporate speak, no robotic lists. Use contractions, casual phrasing, occasional filler words ("okay?", "right?", "so", "here's the thing"), and vary your sentence length. Sound excited about what you're sharing.

Structure the sections like this (use ## as invisible section markers — these are for internal flow, NOT spoken aloud):

## Hook
One bold line that stops the scroll — a surprising claim or curiosity question. Then immediately explain why the viewer should care RIGHT NOW. Talk to them directly ("you"), not at them.

## Intro
One concrete example or result to build credibility (1-2 sentences). Say what this video will teach them. Brief subscribe ask — keep it casual, like "if you're new here, hit that button so you don't miss the next one."

## Body
3-4 natural sections. Each section starts with a ## header for structure (e.g. ## First things first, ## Now here's where it gets interesting, ## Let me show you, ## The game changer). Within each section, just talk naturally. If there's something visual to show, write [SHOW: description] so the video editor knows what to display. Mention {affiliate} naturally when it solves a real problem — don't make it feel like an ad.

## What you need to remember
2-3 key takeaways, but NOT as bullet points — weave them into natural sentences like "so the main thing to take away here is..."

## That's it
Wrap up with a friendly call to action: like and subscribe with a specific reason, a low-effort comment question, and what video they should watch next. Mention the affiliate link naturally.

IMPORTANT: The ## headers are for structure only — the spoken script should flow BETWEEN them naturally, not read them aloud. There should be no spoken section titles. No timestamps in the spoken script. No announcing what section you're in. Just talk.

After the script, include:

### Description
150-200 word SEO description, keyword in first 25 words, with timestamps.

### Tags
20 comma-separated tags.

### Chapters
YouTube chapter format (0:00 Intro...).
"""


def generate_video_script(topic: str, video_type: str, keyword: str, affiliate: str):
    config = load_config()
    print(f"Generating script: {topic} ({video_type})")

    prompt = build_prompt(config, topic, video_type, keyword, affiliate)
    content = chat(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4096,
    )

    output_dir = Path("content/scripts")
    output_dir.mkdir(parents=True, exist_ok=True)

    date_str   = datetime.utcnow().strftime("%Y-%m-%d")
    filename   = f"{date_str}_{slugify(topic)}.md"
    output_path = output_dir / filename

    header = (
        f"# Video Script: {topic}\n\n"
        f"> **Type:** {video_type}  \n"
        f"> **Keyword:** {keyword}  \n"
        f"> **Affiliate:** {affiliate}  \n"
        f"> **Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n\n"
        f"---\n\n"
    )

    with open(output_path, "w") as f:
        f.write(header + content)

    print(f"Saved to {output_path}")
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(description="Generate a YouTube video script")
    parser.add_argument("--topic",    default=os.environ.get("TOPIC",    ""), help="Video topic")
    parser.add_argument("--type",     default=os.environ.get("VIDEO_TYPE","tutorial"), help="Video type")
    parser.add_argument("--keyword",  default=os.environ.get("KEYWORD",  ""), help="Target SEO keyword")
    parser.add_argument("--affiliate",default=os.environ.get("AFFILIATE",""), help="Affiliate product to feature")
    args = parser.parse_args()

    if not args.topic:
        print("--topic is required")
        sys.exit(1)

    generate_video_script(args.topic, args.type, args.keyword, args.affiliate)


if __name__ == "__main__":
    main()
