"""
generate_seo_report.py
Generates a weekly SEO keyword opportunity report using an LLM.
"""

import os
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.llm import chat


def load_config() -> dict:
    with open("config/channel_config.json") as f:
        return json.load(f)


def generate_seo_report():
    config = load_config()
    today = datetime.utcnow()

    prompt = f"""You are an expert YouTube SEO strategist for the channel "{config['channel_name']}".
Niche: {config['niche']}
Audience: {config['target_audience']}
Pillars: {', '.join(config['content_pillars'])}
Report date: {today.strftime('%B %d, %Y')}

Generate a detailed weekly YouTube SEO keyword opportunity report.

## SECTION 1: HIGH-OPPORTUNITY KEYWORDS THIS WEEK
List 15 keywords with strong potential RIGHT NOW. For each:
| Keyword | Est. Monthly Searches | Competition | Search Intent | Best Content Type | Urgency |
Include a mix of: trending (ride the wave), evergreen (long-term), and low-competition gems.

## SECTION 2: TRENDING TOPICS TO COVER FAST
5 AI topics that are trending THIS WEEK.
For each: topic, why it's trending, suggested title, urgency level (hours/days).

## SECTION 3: LONG-TAIL KEYWORD GOLDMINE
10 long-tail keywords (4+ words) with high intent + low competition.
Format as a table with: keyword | intent | suggested title.

## SECTION 4: AFFILIATE-KEYWORD COMBOS
8 keyword opportunities that naturally pair with monetisation.
Format: keyword | affiliate product | estimated CPC tier (Low/Mid/High)

## SECTION 5: VIDEO SERIES IDEA
One video series concept (3-5 videos) based on an underserved keyword cluster.

## SECTION 6: QUICK WINS (Upload These This Week)
Top 3 specific video ideas with full title, based purely on keyword opportunity.

Be specific. Use real AI tool names. Avoid generic advice.
"""

    print(f"Generating SEO report for week of {today.strftime('%B %d, %Y')}")

    content = chat(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=3500,
    )

    output_dir = Path("content/seo")
    output_dir.mkdir(parents=True, exist_ok=True)

    filename    = f"seo_report_{today.strftime('%Y-%m-%d')}.md"
    output_path = output_dir / filename

    header = (
        f"# SEO Keyword Report - Week of {today.strftime('%B %d, %Y')}\n\n"
        f"> **Channel:** {config['channel_name']}  \n"
        f"> **Generated:** {today.strftime('%Y-%m-%d %H:%M')} UTC\n\n"
        f"---\n\n"
    )

    with open(output_path, "w") as f:
        f.write(header + content)

    print(f"Saved to {output_path}")
    return str(output_path)


if __name__ == "__main__":
    generate_seo_report()
