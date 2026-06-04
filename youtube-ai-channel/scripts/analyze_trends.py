"""
analyze_trends.py
Analyzes top YouTube videos and generates content ideas using an LLM.
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
    config_path = Path("config/channel_config.json")
    if not config_path.exists():
        print("config/channel_config.json not found.")
        sys.exit(1)
    with open(config_path) as f:
        return json.load(f)


def slugify(text: str) -> str:
    import re
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:60]


def load_top_videos(filepath: str) -> list:
    with open(filepath) as f:
        data = json.load(f)
    return data.get("videos", [])


def build_analysis_prompt(config: dict, videos: list, content_type: str) -> str:

    video_summaries = []
    for v in videos[:30]:
        video_summaries.append(
            f"- \"{v['title']}\" by {v['channel_title']} "
            f"({v['view_count']:,} views, {v['like_count']:,} likes)"
        )

    videos_text = "\n".join(video_summaries)

    if content_type == "long-form":
        return f"""You are a YouTube strategist for the channel "{config['channel_name']}".
Niche: {config['niche']}
Audience: {config['target_audience']}

Below are the TOP PERFORMING VIDEOS in this niche from the past 30 days.

## TOP VIDEOS ANALYSIS
{videos_text}

## TASK
Based on these top-performing videos, create:

### 1. TREND INSIGHTS (3-5 bullet points)
What patterns do you see? What topics, formats, and hooks are working?

### 2. GAP ANALYSIS
What's missing from the top videos? What angle can we take that hasn't been done?

### 3. VIDEO IDEA (highest opportunity)
- Title (SEO-optimized, ≤70 chars)
- Hook (exact first 5 seconds)
- Structure (4-6 sections with timestamps)
- Why this will work (based on the data above)

### 4. THUMBNAIL CONCEPT
- Visual description
- Text overlay (exact words)
- Color palette
- Emotional angle

### 5. SEO KEYWORDS
- Primary keyword
- 5 secondary keywords
- 20 YouTube tags

### 6. AFFILIATE OPPORTUNITY
Which affiliate from: {', '.join(config['top_affiliates'])} fits best in this video?
Where should it be placed?

Be specific. Use real data from the videos above.
"""
    elif content_type == "shorts":
        return f"""You are a viral YouTube Shorts strategist for "{config['channel_name']}".
Niche: {config['niche']}
Audience: {config['target_audience']}

Below are the TOP PERFORMING VIDEOS in this niche:

{videos_text}

Generate 5 HIGH-POTENTIAL YouTube Shorts ideas based on these trending topics.
Each Short must be completely different.

For EACH short provide:
- Title
- Hook (first 1-2 seconds, pattern interrupt)
- Full 30-60 sec script with [VISUAL] cues
- Thumbnail text overlay
- Hashtags (5)
- Why it will perform well based on the trend data

Format in clean markdown.
"""
    elif content_type == "calendar":
        return f"""You are a YouTube content strategist for "{config['channel_name']}".
Niche: {config['niche']}

Top performing videos in the niche right now:
{videos_text}

Generate a 7-day content calendar that CAPITALIZES on these trends.

Schedule:
- Monday: Long-form (8-15 min)
- Tuesday: Short (30-60 sec)
- Wednesday: Long-form (8-12 min)
- Thursday: Short (30-60 sec)
- Friday: Long-form (10-15 min)
- Saturday: Short (30-60 sec)
- Sunday: Rest

For each day provide: title, hook, keyword, thumbnail concept, affiliate angle, outline, CTA.
"""
    return ""


def analyze_trends(videos_file: str, content_type: str = "long-form"):
    config = load_config()
    videos = load_top_videos(videos_file)

    if not videos:
        print("No videos loaded.")
        sys.exit(1)

    print(f"Analyzing {len(videos)} videos with LLM ({content_type})...")

    prompt = build_analysis_prompt(config, videos, content_type)
    if not prompt:
        print(f"Unknown content type: {content_type}")
        sys.exit(1)

    content = chat(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4000,
    )

    output_dir = Path("content/trends")
    output_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    filename = f"trend_analysis_{content_type}_{date_str}.md"
    output_path = output_dir / filename

    header = (
        f"# Trend Analysis: {content_type}\n\n"
        f"> **Based on top {len(videos)} videos in niche**  \n"
        f"> **Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n\n"
        f"---\n\n"
    )

    with open(output_path, "w") as f:
        f.write(header + content)

    print(f"Analysis saved to {output_path}")
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(description="Analyze YouTube trends with LLM")
    parser.add_argument("--videos-file", required=True,
                        default=os.environ.get("VIDEOS_FILE", ""),
                        help="Path to JSON file from fetch_top_videos.py")
    parser.add_argument("--type", default=os.environ.get("CONTENT_TYPE", "long-form"),
                        choices=["long-form", "shorts", "calendar"],
                        help="Type of content to generate")
    args = parser.parse_args()

    if not args.videos_file:
        print("--videos-file is required")
        sys.exit(1)

    analyze_trends(args.videos_file, args.type)


if __name__ == "__main__":
    main()
