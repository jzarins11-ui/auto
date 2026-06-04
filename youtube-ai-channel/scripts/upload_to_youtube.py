"""
upload_to_youtube.py
Uploads videos to YouTube via OAuth 2.0 with full metadata.
Supports local use (interactive OAuth) and CI (refresh token env vars).

Setup:
  1. https://console.cloud.google.com -> Create Project -> Enable YouTube Data API v3
  2. Credentials -> OAuth 2.0 Client ID -> Desktop app -> Download JSON
  3. Save as config/youtube_credentials.json OR paste contents into .env:
     YT_CLIENT_ID=...
     YT_CLIENT_SECRET=...
  4. Run this script once locally to generate refresh token
  5. Set YT_REFRESH_TOKEN in .env for non-interactive / CI use
"""

import os
import json
import sys
import argparse
import webbrowser
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = Path("config/youtube_token.json")
CREDS_FILE = Path("config/youtube_credentials.json")
REDIRECT_PORT = 8080


def load_env_credentials() -> dict | None:
    client_id = os.environ.get("YT_CLIENT_ID")
    client_secret = os.environ.get("YT_CLIENT_SECRET")
    if client_id and client_secret:
        return {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [f"http://localhost:{REDIRECT_PORT}"],
            }
        }
    return None


def get_credentials():
    creds = None

    if TOKEN_FILE.exists():
        with open(TOKEN_FILE) as f:
            creds = Credentials.from_authorized_user_info(json.load(f), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        return creds

    if creds and creds.valid:
        return creds

    client_config = load_env_credentials()
    if not client_config and CREDS_FILE.exists():
        with open(CREDS_FILE) as f:
            client_config = json.load(f)

    if not client_config:
        print("No OAuth credentials found.")
        print("Options:")
        print(f"  1. Save OAuth client JSON as {CREDS_FILE}")
        print("  2. Set YT_CLIENT_ID + YT_CLIENT_SECRET in .env")
        print("  3. Set YT_REFRESH_TOKEN in .env for headless use")
        refresh = os.environ.get("YT_REFRESH_TOKEN")
        if refresh:
            return Credentials(
                token=None,
                refresh_token=refresh,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=os.environ.get("YT_CLIENT_ID", ""),
                client_secret=os.environ.get("YT_CLIENT_SECRET", ""),
                scopes=SCOPES,
            )
        sys.exit(1)

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=REDIRECT_PORT, open_browser=True)

    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
    print(f"Token saved to {TOKEN_FILE}")
    print(f"\nFor CI/headless use, add these to your .env:")
    print(f"  YT_CLIENT_ID={creds.client_id}")
    print(f"  YT_CLIENT_SECRET=<your_client_secret>")
    print(f"  YT_REFRESH_TOKEN={creds.refresh_token}")

    return creds


def upload_video(
    creds,
    video_path: str,
    title: str,
    description: str = "",
    tags: list[str] | None = None,
    category_id: str = "28",
    privacy_status: str = "public",
    thumbnail_path: str | None = None,
):
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or [],
            "categoryId": category_id,
        },
        "status": {"privacyStatus": privacy_status, "selfDeclaredMadeForKids": False},
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)

    request = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploaded {int(status.progress() * 100)}%")

    video_id = response["id"]
    print(f"Uploaded: https://youtu.be/{video_id}")

    if thumbnail_path and os.path.exists(thumbnail_path):
        youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumbnail_path)).execute()
        print(f"Thumbnail set: {thumbnail_path}")

    return video_id


def main():
    parser = argparse.ArgumentParser(description="Upload video to YouTube")
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("--title", help="Video title (reads from script file if omitted)")
    parser.add_argument("--description", help="Video description")
    parser.add_argument("--tags", nargs="*", default=[], help="Space-separated tags")
    parser.add_argument("--category", default="28", help="YouTube category ID (default: 28=Science & Technology)")
    parser.add_argument("--privacy", choices=["public", "unlisted", "private"], default="public")
    parser.add_argument("--thumbnail", help="Path to thumbnail image")
    parser.add_argument("--meta-file", help="Path to generated _meta.md file (reads title/desc/tags)")
    args = parser.parse_args()

    if not os.path.exists(args.video):
        print(f"Video file not found: {args.video}")
        sys.exit(1)

    title = args.title
    description = args.description or ""
    tags = args.tags or []

    if args.meta_file and os.path.exists(args.meta_file):
        with open(args.meta_file) as f:
            content = f.read()
        lines = content.split("\n")
        for line in lines:
            if line.startswith("# Title:"):
                title = title or line.split(":", 1)[1].strip()
            elif line.startswith("# Description:"):
                description = description or line.split(":", 1)[1].strip()
            elif line.startswith("# Tags:"):
                tags = tags or [t.strip() for t in line.split(":", 1)[1].split(",")]

    if not title:
        title = os.path.splitext(os.path.basename(args.video))[0]

    creds = get_credentials()
    upload_video(creds, args.video, title, description, tags, args.category, args.privacy, args.thumbnail)


if __name__ == "__main__":
    main()
