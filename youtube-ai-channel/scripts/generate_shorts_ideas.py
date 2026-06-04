"""
generate_shorts_ideas.py
Generates 3 viral YouTube Shorts ideas for the day using an LLM.
"""

import os
import json
from datetime import datetime
from pathlib import Path

from scripts.llm import chat


def load_config() -> dict:
    with open("config/channel_config.json") as f:
        return json.load(f)


def generate_shorts_ideas():
    config = load_config()
    today = datetime.utcnow()

    prompt = f"""You are a viral YouTube Shorts strategist for the channel "{config['channel_name']}".
Niche: {config['niche']}
Audience: {config['target_audience']}
Today: {today.strftime('%A, %B %d, %Y')}

Generate 3 YouTube Shorts ideas for today. Each should be DIFFERENT in style:
- Idea 1: "Did you know?" - a shocking AI fact or tool capability
- Idea 2: Quick tutorial - "Do X in 30 seconds with AI"
- Idea 3: Reaction / listicle - "Top 3 AI tools for [specific task]"

For EACH Short include:

### SHORT #N: [Title]
**Hook (first 1-2 seconds):** [Exact opening line - pattern interrupt]
**Duration:** [15 / 30 / 45 / 60 seconds]
**Full Script:**
[Complete word-for-word script with [VISUAL] cues]
**Thumbnail Text:** [Bold 3-5 word overlay text]
**Hashtags:** [5 relevant hashtags]
**Best Time to Post:** [e.g., 2 PM your local time]
**Viral Potential:** [High / Medium] + one-line reason

Rules:
- Scripts must be fast-paced - no filler words
- Start with a pattern interrupt (never "Hey guys")
- Show a real AI result on screen whenever possible
- End with a cliffhanger or strong CTA ("Follow for daily AI tools")
- Keep language simple - 8th grade reading level
"""

    print(f"Generating Shorts ideas for {today.strftime('%A %B %d')}")

    content = chat(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048,
    )

    output_dir = Path("content/shorts")
    output_dir.mkdir(parents=True, exist_ok=True)

    filename    = f"shorts_{today.strftime('%Y-%m-%d')}.md"
    output_path = output_dir / filename

    header = (
        f"# Daily Shorts Ideas - {today.strftime('%A, %B %d, %Y')}\n\n"
        f"> **Channel:** {config['channel_name']}  \n"
        f"> **Generated:** {today.strftime('%Y-%m-%d %H:%M')} UTC\n\n"
        f"---\n\n"
    )

    with open(output_path, "w") as f:
        f.write(header + content)

    print(f"Saved to {output_path}")
    return str(output_path)


if __name__ == "__main__":
    generate_shorts_ideas()
