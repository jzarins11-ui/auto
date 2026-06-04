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

    return f"""You are an expert YouTube scriptwriter for the channel "{config['channel_name']}".
Niche: {config['niche']}
Audience: {config['target_audience']}

VIDEO REQUEST:
- Topic:      {topic}
- Type:       {video_type} - {type_guidance}
- Keyword:    {keyword}
- Affiliate:  {affiliate}

Write a COMPLETE, ready-to-record video script. Use this proven structure:

## HOOK (0:00-0:08)
3-second opening line that stops the scroll. Make a bold claim or ask a curiosity question.
Then 5-second context setter - why this matters RIGHT NOW.

## INTRO (0:08-0:45)
- Reinforce the promise with one concrete result/example
- Brief credibility statement (1 sentence)
- "In this video you'll learn exactly how to [X]"
- Subscribe nudge (natural, not begging)

## MAIN CONTENT
Break into 3-5 clearly labelled sections (e.g., ## STEP 1: ...).
For each section:
- [ON SCREEN] direction for what to show/type/click
- Spoken script (conversational, not robotic)
- Any relevant tip or gotcha

## AFFILIATE MENTION (natural placement within main content)
Weave in {affiliate} organically - show it solving a real problem in the video.

## RECAP (1 min before end)
3-bullet summary of key takeaways.

## CALL TO ACTION (final 30 sec)
- Like + subscribe ask (specific reason why)
- Comment prompt (low-friction question)
- Next video recommendation (related topic)
- Link mention (affiliate + any freebie)

ALSO GENERATE (after the script):
### VIDEO DESCRIPTION (YouTube)
SEO-rich description, 150-200 words, primary keyword in first 25 words.
Include timestamps.
Include affiliate disclaimer line.

### TAGS
20 YouTube tags (comma-separated), mix of broad and long-tail.

### CHAPTERS
Timestamp chapters in YouTube format (0:00 Intro, etc.).

Write in a natural, conversational, energetic tone. No corporate-speak.
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
