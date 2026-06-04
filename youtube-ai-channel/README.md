# YouTube AI Channel Automation

GitHub-powered automation that generates content calendars, video scripts, Shorts ideas, SEO reports, and trend analysis — auto-committed on a schedule.

## When things run

| Workflow | When it runs |
|---|---|
| **Weekly Content Calendar** | Every Monday 7am UTC |
| **Daily Shorts Ideas** | Every day 6am UTC |
| **Weekly SEO Report** | Every Sunday 8am UTC |
| **Generate Video Script** | You click "Run workflow" + fill in a form |
| **Generate Description & Tags** | You click "Run workflow" + fill in a form |
| **Fetch Top Videos + Trend Analysis** | You click "Run workflow" + fill in a form |

## Quick setup

### 1. Push to a private GitHub repo
```bash
git init && git add . && git commit -m "setup" && git push
```

### 2. Add your secrets
In GitHub repo **Settings → Secrets and Variables → Actions → New repository secret**:

| Secret | Where to get it |
|---|---|
| `ANTHROPIC_API_KEY` (or `DEEPSEEK_API_KEY`) | console.anthropic.com or platform.deepseek.com |
| `YOUTUBE_API_KEY` | console.cloud.google.com → YouTube Data API v3 |

### 3. Edit config
Edit `config/channel_config.json` — plug in your channel name, niche, and affiliates.

### 4. Run your first workflow
**Actions → Weekly Content Calendar → Run workflow**

Everything else runs on autopilot from there.

## Project structure

```
├── .github/workflows/
│   ├── weekly-content-calendar.yml    # Mon 7am UTC
│   ├── daily-shorts-ideas.yml         # Daily 6am UTC
│   ├── weekly-seo-report.yml          # Sun 8am UTC
│   ├── generate-video-script.yml      # Manual trigger
│   └── generate-description-tags.yml  # Manual trigger
├── scripts/
│   ├── llm.py                    # LLM backend (DeepSeek/Claude)
│   ├── fetch_top_videos.py       # YouTube API -> top 100 videos
│   ├── analyze_trends.py         # Trend analysis + ideas
│   ├── generate_content_calendar.py
│   ├── generate_video_script.py
│   ├── generate_shorts_ideas.py
│   ├── generate_seo_report.py
│   └── generate_description_tags.py
├── config/channel_config.json    # ← Edit this
└── requirements.txt
```

## Run locally

```bash
pip install -r requirements.txt

# Set your keys
export DEEPSEEK_API_KEY=sk-...
export YOUTUBE_API_KEY=AIzaSy...

# Generate a content calendar
python scripts/generate_content_calendar.py

# Fetch trending videos in your niche
python scripts/fetch_top_videos.py --max-results 50

# Analyze trends + generate ideas
python scripts/analyze_trends.py --videos-file output/trends/top_videos_*.json

# Generate a video script
python scripts/generate_video_script.py \
  --topic "Best free AI tools 2026" \
  --type tutorial \
  --keyword "free AI tools" \
  --affiliate "Claude Pro"

# Generate description + tags
python scripts/generate_description_tags.py \
  --title "I Tested 10 AI Tools" \
  --keyword "best AI tools" \
  --affiliate "Claude Pro" \
  --duration 12
```
