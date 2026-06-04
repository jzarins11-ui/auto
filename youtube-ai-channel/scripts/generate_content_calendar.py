"""
generate_content_calendar.py
Generates a 7-day YouTube content calendar using an LLM.
"""

import os
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from scripts.llm import chat


def load_config() -> dict:
    config_path = Path("config/channel_config.json")
    if not config_path.exists():
        print("config/channel_config.json not found.")
        sys.exit(1)
    with open(config_path) as f:
        return json.load(f)


def get_week_monday() -> datetime:
    today = datetime.utcnow()
    return today - timedelta(days=today.weekday())


def generate_content_calendar():
    config = load_config()

    week_start = get_week_monday()
    week_end   = week_start + timedelta(days=6)

    prompt = f"""You are an expert YouTube content strategist specialising in AI tools channels.

CHANNEL:
- Name: {config['channel_name']}
- Tagline: {config['tagline']}
- Niche: {config['niche']}
- Audience: {config['target_audience']}
- Pillars: {', '.join(config['content_pillars'])}
- Monetisation focus: {', '.join(config['monetization_focus'])}
- Top affiliate products: {', '.join(config['top_affiliates'])}

WEEK: {week_start.strftime('%B %d')} - {week_end.strftime('%B %d, %Y')}

POSTING SCHEDULE:
- Monday:    Long-form Tutorial (8-15 min)
- Tuesday:   Daily Short (30-60 sec)
- Wednesday: AI Money-Making / Case Study (8-12 min)
- Thursday:  Daily Short (30-60 sec)
- Friday:    Tool Comparison or Roundup (10-15 min)
- Saturday:  Daily Short (30-60 sec)
- Sunday:    Rest

For EACH piece of content provide:
1. Title - YouTube SEO-optimized, ≤70 chars, high curiosity + clear value
2. Hook - exact first 3 seconds of script (one punchy sentence)
3. Primary Keyword - the main SEO keyword to target
4. Secondary Keywords - 3 related keywords (comma-separated)
5. Thumbnail Concept - specific visual description (colours, text overlay, facial expression if needed)
6. Affiliate Angle - which product to promote + natural placement in video
7. Content Outline - 5-7 bullet points for long-form, 3 for Shorts
8. CTA - specific call-to-action for end of video/Short
9. Monetisation Potential - Low / Medium / High + one-line reason

Be specific and actionable. Reference real trending AI tools. Format in clean markdown.
"""

    print(f"Generating content calendar for {week_start.strftime('%B %d, %Y')}")

    content = chat(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4096,
    )

    output_dir = Path("content/calendars")
    output_dir.mkdir(parents=True, exist_ok=True)

    filename    = f"calendar_{week_start.strftime('%Y-%m-%d')}.md"
    output_path = output_dir / filename

    header = (
        f"# Content Calendar: {week_start.strftime('%B %d')} - "
        f"{week_end.strftime('%B %d, %Y')}\n\n"
        f"> **Channel:** {config['channel_name']}  \n"
        f"> **Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC  \n\n"
        f"---\n\n"
    )

    with open(output_path, "w") as f:
        f.write(header + content)

    print(f"Saved to {output_path}")
    return str(output_path)


if __name__ == "__main__":
    generate_content_calendar()
