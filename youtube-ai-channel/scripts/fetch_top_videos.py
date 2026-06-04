"""
fetch_top_videos.py
Fetches top 100 most-viewed YouTube videos in the channel's niche
using YouTube Data API v3. Used by the trend analysis pipeline.
"""

import os
import json
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


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


def fetch_top_videos(
    api_key: str,
    query: str = None,
    max_results: int = 50,
    days_back: int = 30,
    region_code: str = "US",
) -> list:
    """
    Fetch top videos from YouTube sorted by view count.
    If query is provided, search by keyword. Otherwise, fetch trending.
    """
    youtube = build("youtube", "v3", developerKey=api_key)

    published_after = (datetime.utcnow() - timedelta(days=days_back)).isoformat("T") + "Z"

    all_videos = []

    if query:
        request = youtube.search().list(
            q=query,
            part="snippet",
            type="video",
            maxResults=min(max_results, 50),
            publishedAfter=published_after,
            regionCode=region_code,
            order="viewCount",
        )
    else:
        request = youtube.videos().list(
            chart="mostPopular",
            part="snippet,statistics",
            maxResults=min(max_results, 50),
            regionCode=region_code,
        )

    try:
        while request and len(all_videos) < max_results:
            response = request.execute()

            for item in response.get("items", []):
                video = {
                    "video_id": item["id"],
                    "title": item["snippet"]["title"],
                    "channel_title": item["snippet"]["channelTitle"],
                    "published_at": item["snippet"]["publishedAt"],
                    "description": item["snippet"]["description"][:500],
                    "tags": item["snippet"].get("tags", []),
                    "category_id": item["snippet"]["categoryId"],
                    "thumbnails": item["snippet"]["thumbnails"]["high"]["url"],
                }

                if "statistics" in item:
                    stats = item["statistics"]
                    video["view_count"] = int(stats.get("viewCount", 0))
                    video["like_count"] = int(stats.get("likeCount", 0))
                    video["comment_count"] = int(stats.get("commentCount", 0))
                else:
                    video["view_count"] = 0
                    video["like_count"] = 0
                    video["comment_count"] = 0

                all_videos.append(video)

            if len(all_videos) >= max_results:
                break

            if "nextPageToken" in response:
                if query:
                    request = youtube.search().list_next(request, response)
                else:
                    request = youtube.videos().list_next(request, response)
            else:
                break

    except HttpError as e:
        print(f"YouTube API error: {e}")
        return all_videos

    all_videos.sort(key=lambda v: v["view_count"], reverse=True)
    return all_videos[:max_results]


def main():
    parser = argparse.ArgumentParser(description="Fetch top YouTube videos")
    parser.add_argument("--query", default=os.environ.get("YOUTUBE_QUERY", ""),
                        help="Search query (defaults to niche from config)")
    parser.add_argument("--max-results", type=int,
                        default=int(os.environ.get("MAX_RESULTS", "50")),
                        help="Number of videos to fetch (max 100)")
    parser.add_argument("--days-back", type=int,
                        default=int(os.environ.get("DAYS_BACK", "30")),
                        help="How many days back to search")
    parser.add_argument("--region", default=os.environ.get("REGION", "US"),
                        help="Region code (e.g. US, IN, GB)")
    parser.add_argument("--output", default="",
                        help="Output file path (default: content/trends/)")
    args = parser.parse_args()

    config = load_config()
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("YOUTUBE_API_KEY environment variable is required")
        sys.exit(1)

    query = args.query or config.get("niche", "")

    print(f"Fetching top {args.max_results} videos for query: '{query}' "
          f"(past {args.days_back} days, region: {args.region})")

    videos = fetch_top_videos(
        api_key=api_key,
        query=query,
        max_results=args.max_results,
        days_back=args.days_back,
        region_code=args.region,
    )

    if not videos:
        print("No videos found.")
        sys.exit(1)

    print(f"Found {len(videos)} videos")

    output_dir = Path(args.output) if args.output else Path("content/trends")
    output_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    query_slug = slugify(query)
    filename = f"top_videos_{date_str}_{query_slug}.json"
    output_path = output_dir / filename

    output_data = {
        "query": query,
        "region": args.region,
        "days_back": args.days_back,
        "fetched_at": datetime.utcnow().isoformat(),
        "total_fetched": len(videos),
        "videos": videos,
    }

    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"Saved {len(videos)} videos to {output_path}")

    summary_path = output_dir / f"top_videos_{date_str}_{query_slug}_summary.txt"
    with open(summary_path, "w") as f:
        f.write(f"Top {len(videos)} Videos for '{query}'\n")
        f.write(f"Fetched: {date_str}\n\n")
        for i, v in enumerate(videos[:20], 1):
            f.write(f"{i:2d}. {v['view_count']:>8,} views | {v['title']}\n")
            f.write(f"       {v['channel_title']} | https://youtu.be/{v['video_id']}\n")

    print(f"Summary saved to {summary_path}")
    print(json.dumps({
        "status": "success",
        "videos_fetched": len(videos),
        "output_file": str(output_path),
    }))


if __name__ == "__main__":
    main()
