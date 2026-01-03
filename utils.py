"""Utility functions for retrieving YouTube channel videos and transcripts."""

import os
import time
from pathlib import Path
from typing import List, Optional, Tuple

import requests
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi

# Load environment variables from .env file
load_dotenv()


def load_config_from_env() -> Tuple[str, str]:
    """
    Load YouTube API key and channel ID from environment variables (.env file).

    Returns:
        Tuple of (api_key, channel_id)

    Raises:
        ValueError: If required environment variables are not set
    """
    api_key = os.getenv("YOUTUBE_API_KEY")
    channel_id = os.getenv("YOUTUBE_CHANNEL_ID")

    if not api_key:
        raise ValueError(
            "YOUTUBE_API_KEY not found in environment variables. "
            "Please set it in your .env file or as an environment variable."
        )

    if not channel_id:
        raise ValueError(
            "YOUTUBE_CHANNEL_ID not found in environment variables. "
            "Please set it in your .env file or as an environment variable."
        )

    return api_key, channel_id


def get_channel_uploads_playlist_id(
    channel_id: str, api_key: str, delay: float = 1.0
) -> str:
    """
    Get the uploads playlist ID for a given YouTube channel.

    Args:
        channel_id: The YouTube channel ID
        api_key: YouTube Data API v3 key
        delay: Delay in seconds after the request (default: 1.0)

    Returns:
        The uploads playlist ID

    Raises:
        requests.RequestException: If the API request fails
        KeyError: If the uploads playlist ID cannot be found
    """
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {"part": "contentDetails", "id": channel_id, "key": api_key}

    response = requests.get(url, params=params)
    response.raise_for_status()

    # Add delay to avoid rate limiting
    time.sleep(delay)

    data = response.json()
    if not data.get("items"):
        raise ValueError(f"No channel found with ID: {channel_id}")

    uploads_playlist_id = data["items"][0]["contentDetails"]["relatedPlaylists"][
        "uploads"
    ]
    return uploads_playlist_id


def get_all_video_ids(
    channel_id: str,
    api_key: str,
    max_results: Optional[int] = None,
    api_delay: float = 1.0,
) -> List[str]:
    """
    Get all video IDs from a channel, ordered from latest to oldest.

    Args:
        channel_id: The YouTube channel ID
        api_key: YouTube Data API v3 key
        max_results: Optional maximum number of videos to retrieve. If None, retrieves all.
        api_delay: Delay in seconds between API requests (default: 1.0)

    Returns:
        List of video IDs ordered from latest to oldest
    """
    # Get the uploads playlist ID
    uploads_playlist_id = get_channel_uploads_playlist_id(
        channel_id, api_key, delay=api_delay
    )

    video_ids = []
    next_page_token = None
    url = "https://www.googleapis.com/youtube/v3/playlistItems"

    while True:
        params = {
            "part": "snippet",
            "playlistId": uploads_playlist_id,
            "maxResults": 50,  # Maximum allowed per request
            "key": api_key,
        }

        if next_page_token:
            params["pageToken"] = next_page_token

        response = requests.get(url, params=params)
        response.raise_for_status()

        # Add delay to avoid rate limiting
        time.sleep(api_delay)

        data = response.json()

        # Extract video IDs from this page
        for item in data.get("items", []):
            video_id = item["snippet"]["resourceId"]["videoId"]
            video_ids.append(video_id)

            # Check if we've reached the max_results limit
            if max_results and len(video_ids) >= max_results:
                return video_ids[:max_results]

        # Check if there are more pages
        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break

    return video_ids


def download_transcript(
    video_id: str, languages: Optional[List[str]] = None
) -> Optional[str]:
    """
    Download transcript for a given video ID.

    Args:
        video_id: The YouTube video ID
        languages: Optional list of language codes to try (e.g., ['en', 'es']).
                   If None, tries to fetch any available transcript.

    Returns:
        Transcript text as a string, or None if no transcript is available
    """
    try:
        ytt_api = YouTubeTranscriptApi()

        if languages:
            transcript = ytt_api.fetch(video_id, languages=languages)
        else:
            transcript = ytt_api.fetch(video_id)

        # Combine all transcript entries into a single text
        transcript_text = "\n".join([entry["text"] for entry in transcript])
        return transcript_text
    except Exception as e:
        print(f"Error downloading transcript for video {video_id}: {e}")
        return None


def save_transcript(
    video_id: str, transcript_text: str, output_dir: str = "transcriptions"
) -> Path:
    """
    Save transcript text to a markdown file.

    Args:
        video_id: The YouTube video ID
        transcript_text: The transcript text to save
        output_dir: Directory to save transcripts in (default: "transcriptions")

    Returns:
        Path to the saved file
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    file_path = output_path / f"{video_id}.md"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"# Transcript for Video: {video_id}\n\n")
        f.write(f"Video URL: https://www.youtube.com/watch?v={video_id}\n\n")
        f.write("---\n\n")
        f.write(transcript_text)

    return file_path


def download_channel_transcripts(
    channel_id: str,
    api_key: str,
    output_dir: str = "transcriptions",
    max_videos: Optional[int] = None,
    languages: Optional[List[str]] = None,
    skip_existing: bool = True,
    api_delay: float = 1.0,
    transcript_delay: float = 0.5,
) -> dict:
    """
    Download transcripts for all videos from a channel.

    Args:
        channel_id: The YouTube channel ID
        api_key: YouTube Data API v3 key
        output_dir: Directory to save transcripts in (default: "transcriptions")
        max_videos: Optional maximum number of videos to process
        languages: Optional list of language codes to try for transcripts
        skip_existing: If True, skip videos that already have transcripts saved
        api_delay: Delay in seconds between YouTube Data API requests (default: 1.0)
        transcript_delay: Delay in seconds between transcript downloads (default: 0.5)

    Returns:
        Dictionary with statistics about the download process
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Get all video IDs
    print(f"Fetching video IDs for channel {channel_id}...")
    video_ids = get_all_video_ids(
        channel_id, api_key, max_results=max_videos, api_delay=api_delay
    )
    print(f"Found {len(video_ids)} videos")

    stats = {
        "total_videos": len(video_ids),
        "downloaded": 0,
        "skipped": 0,
        "failed": 0,
        "failed_videos": [],
    }

    # Download transcripts for each video
    for i, video_id in enumerate(video_ids, 1):
        file_path = output_path / f"{video_id}.md"

        # Skip if file already exists
        if skip_existing and file_path.exists():
            print(f"[{i}/{len(video_ids)}] Skipping {video_id} (already exists)")
            stats["skipped"] += 1
            continue

        print(f"[{i}/{len(video_ids)}] Downloading transcript for {video_id}...")
        transcript_text = download_transcript(video_id, languages=languages)

        # Add delay after transcript download to avoid rate limiting
        time.sleep(transcript_delay)

        if transcript_text:
            save_transcript(video_id, transcript_text, output_dir)
            stats["downloaded"] += 1
            print(f"  ✓ Saved transcript to {file_path}")
        else:
            stats["failed"] += 1
            stats["failed_videos"].append(video_id)
            print("  ✗ Failed to download transcript")

    return stats
