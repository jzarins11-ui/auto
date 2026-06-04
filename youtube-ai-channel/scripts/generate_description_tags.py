"""
generate_description_tags.py
Generates SEO-optimized description, tags, chapters, and pinned comment.
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


def generate_description_tags(title: str, keyword: str, affiliate: str, duration_min: int):
    config = load_config()

    prompt = f"""You are a YouTube SEO expert writing for the channel "{config['channel_name']}".
Niche: {config['niche']}
Audience: {config['target_audience']}

VIDEO:
- Title:     {title}
- Keyword:   {keyword}
- Affiliate: {affiliate}
- Duration:  ~{duration_min} minutes

Generate the following, clearly separated by headers:

## YOUTUBE DESCRIPTION
Write a 180-220 word SEO-optimized video description.
Rules:
- Primary keyword "{keyword}" must appear in the FIRST 25 words
- Include 2-3 secondary keywords naturally
- Plain language, conversational
- Short paragraphs (2-3 sentences max)
- End with a CTA paragraph: subscribe, comment, and follow
- Final line: affiliate disclaimer

## HASHTAGS (for description footer)
3 hashtags only

## YOUTUBE TAGS
25 tags, comma-separated. Mix of exact match, broad, long-tail.

## CHAPTER TIMESTAMPS
Realistic chapters for a {duration_min}-minute video on "{title}".
Format:
0:00 Introduction
0:45 [Section name]
Include 6-10 chapters.

## PINNED COMMENT
Write a pinned comment (100-130 words) to post immediately after upload.
Answer a likely viewer question, add extra value, mention the affiliate link naturally.
"""

    print(f"Generating description & tags for: {title}")

    content = chat(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048,
    )

    output_dir = Path("content/scripts")
    output_dir.mkdir(parents=True, exist_ok=True)

    date_str    = datetime.utcnow().strftime("%Y-%m-%d")
    filename    = f"{date_str}_{slugify(title)}_meta.md"
    output_path = output_dir / filename

    header = (
        f"# Video Metadata: {title}\n\n"
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
    parser = argparse.ArgumentParser(description="Generate YouTube description, tags & chapters")
    parser.add_argument("--title",    default=os.environ.get("VIDEO_TITLE",    ""), help="Video title")
    parser.add_argument("--keyword",  default=os.environ.get("KEYWORD",        ""), help="Primary SEO keyword")
    parser.add_argument("--affiliate",default=os.environ.get("AFFILIATE",      ""), help="Affiliate to mention")
    parser.add_argument("--duration", default=int(os.environ.get("DURATION", 10)),   type=int, help="Video duration in minutes")
    args = parser.parse_args()

    if not args.title:
        print("--title is required")
        sys.exit(1)

    generate_description_tags(args.title, args.keyword, args.affiliate, args.duration)


if __name__ == "__main__":
    main()
