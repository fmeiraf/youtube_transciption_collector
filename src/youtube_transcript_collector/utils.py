"""Utility functions for retrieving YouTube channel videos and transcripts."""

import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.table import Table
from youtube_transcript_api import YouTubeTranscriptApi

console = Console()

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

    if not api_key:
        raise ValueError(
            "YOUTUBE_API_KEY not found in environment variables. "
            "Please set it in your .env file or as an environment variable."
        )

    return api_key


def get_channel_id(identifier: str, api_key: str, delay: float = 1.0) -> str:
    """
    Get channel ID from various identifier types (username, handle, URL, or channel ID).

    Args:
        identifier: Can be:
            - Channel ID (e.g., "UC-lHJZR3Gqxm24_Vd_AJ5Yw") - returns as-is
            - Channel handle (e.g., "@channelname" or "channelname")
            - Channel username (e.g., "channelname")
            - Channel URL (e.g., "https://www.youtube.com/channel/UC...")
            - Channel custom URL (e.g., "https://www.youtube.com/c/channelname")
        api_key: YouTube Data API v3 key
        delay: Delay in seconds after the request (default: 1.0)

    Returns:
        The channel ID (e.g., "UC-lHJZR3Gqxm24_Vd_AJ5Yw")

    Raises:
        ValueError: If the channel cannot be found or identifier is invalid
        requests.RequestException: If the API request fails
    """
    # If it's already a channel ID (starts with UC), return it
    if identifier.startswith("UC") and len(identifier) == 24:
        return identifier

    # Extract identifier from URL if it's a URL
    if "youtube.com" in identifier or "youtu.be" in identifier:
        # Extract channel ID from URL like https://www.youtube.com/channel/UC...
        if "/channel/" in identifier:
            channel_id = identifier.split("/channel/")[-1].split("?")[0].split("/")[0]
            if channel_id.startswith("UC") and len(channel_id) == 24:
                return channel_id

        # Extract username/handle from custom URL like https://www.youtube.com/c/channelname
        if "/c/" in identifier:
            username = identifier.split("/c/")[-1].split("?")[0].split("/")[0]
            identifier = username
        elif "/user/" in identifier:
            username = identifier.split("/user/")[-1].split("?")[0].split("/")[0]
            identifier = username
        elif "/@" in identifier:
            handle = identifier.split("/@")[-1].split("?")[0].split("/")[0]
            identifier = f"@{handle}"

    # Remove @ if present (for handles)
    if identifier.startswith("@"):
        handle = identifier[1:]
    else:
        handle = identifier
        username = identifier

    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {"part": "id", "key": api_key}

    # Try handle first (newer format, e.g., @channelname)
    if identifier.startswith("@"):
        params["forHandle"] = handle
    else:
        # Try username (older format)
        params["forUsername"] = username

    response = requests.get(url, params=params)
    response.raise_for_status()

    # Add delay to avoid rate limiting
    time.sleep(delay)

    data = response.json()

    if data.get("items") and len(data["items"]) > 0:
        return data["items"][0]["id"]

    # If handle didn't work, try username (or vice versa)
    if identifier.startswith("@"):
        # Try as username instead
        params = {"part": "id", "key": api_key, "forUsername": handle}
        response = requests.get(url, params=params)
        response.raise_for_status()
        time.sleep(delay)
        data = response.json()

        if data.get("items") and len(data["items"]) > 0:
            return data["items"][0]["id"]

    raise ValueError(
        f"Channel not found for identifier: {identifier}. "
        "Make sure it's a valid channel ID, handle (@channelname), username, or URL."
    )


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


def get_video_metadata(
    video_ids: List[str], api_key: str, api_delay: float = 1.0
) -> Dict[str, Dict]:
    """
    Get metadata for a list of video IDs.
    
    Args:
        video_ids: List of YouTube video IDs
        api_key: YouTube Data API v3 key
        api_delay: Delay in seconds between API requests (default: 1.0)
    
    Returns:
        Dictionary mapping video_id to metadata dict with keys like:
        - title
        - description
        - publishedAt
        - channelTitle
        - duration (if available)
    """
    metadata = {}
    
    # YouTube API allows up to 50 video IDs per request
    batch_size = 50
    url = "https://www.googleapis.com/youtube/v3/videos"
    
    for i in range(0, len(video_ids), batch_size):
        batch = video_ids[i:i + batch_size]
        
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": ",".join(batch),
            "key": api_key,
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        # Add delay to avoid rate limiting
        time.sleep(api_delay)
        
        data = response.json()
        
        for item in data.get("items", []):
            video_id = item["id"]
            snippet = item.get("snippet", {})
            content_details = item.get("contentDetails", {})
            statistics = item.get("statistics", {})
            
            metadata[video_id] = {
                "title": snippet.get("title", "Unknown Title"),
                "description": snippet.get("description", ""),
                "publishedAt": snippet.get("publishedAt", ""),
                "channelTitle": snippet.get("channelTitle", ""),
                "duration": content_details.get("duration", ""),
                "viewCount": statistics.get("viewCount", "0"),
                "likeCount": statistics.get("likeCount", "0"),
            }
    
    return metadata


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
        # FetchedTranscriptSnippet objects have .text attribute, not dictionary access
        transcript_text = "\n".join([entry.text for entry in transcript])
        return transcript_text
    except Exception as e:
        console.print(f"[red]Error downloading transcript for video {video_id}: {e}[/red]")
        return None


def save_transcript(
    video_id: str,
    transcript_text: str,
    output_dir: str = "transcriptions",
    metadata: Optional[Dict] = None,
) -> Path:
    """
    Save transcript text to a markdown file.

    Args:
        video_id: The YouTube video ID
        transcript_text: The transcript text to save
        output_dir: Directory to save transcripts in (default: "transcriptions")
        metadata: Optional dictionary with video metadata (title, description, etc.)

    Returns:
        Path to the saved file
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    file_path = output_path / f"{video_id}.md"

    with open(file_path, "w", encoding="utf-8") as f:
        # Use title from metadata if available, otherwise use video_id
        title = metadata.get("title", video_id) if metadata else video_id
        
        f.write(f"# {title}\n\n")
        f.write(f"**Video ID:** {video_id}\n\n")
        f.write(f"**Video URL:** https://www.youtube.com/watch?v={video_id}\n\n")
        
        if metadata:
            if metadata.get("channelTitle"):
                f.write(f"**Channel:** {metadata['channelTitle']}\n\n")
            if metadata.get("publishedAt"):
                f.write(f"**Published:** {metadata['publishedAt']}\n\n")
            if metadata.get("duration"):
                f.write(f"**Duration:** {metadata['duration']}\n\n")
            if metadata.get("viewCount"):
                f.write(f"**Views:** {metadata['viewCount']}\n\n")
            if metadata.get("description"):
                f.write("## Description\n\n")
                f.write(f"{metadata['description']}\n\n")
        
        f.write("---\n\n")
        f.write("## Transcript\n\n")
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
    console.print(f"[cyan]🔍 Fetching video IDs for channel [bold]{channel_id}[/bold]...[/cyan]")
    video_ids = get_all_video_ids(
        channel_id, api_key, max_results=max_videos, api_delay=api_delay
    )
    console.print(f"[green]✓ Found [bold]{len(video_ids)}[/bold] videos[/green]\n")

    # Fetch video metadata
    console.print(f"[cyan]📋 Fetching video metadata...[/cyan]")
    video_metadata = get_video_metadata(video_ids, api_key, api_delay=api_delay)
    console.print(f"[green]✓ Retrieved metadata for [bold]{len(video_metadata)}[/bold] videos[/green]\n")

    stats = {
        "total_videos": len(video_ids),
        "downloaded": 0,
        "skipped": 0,
        "failed": 0,
        "failed_videos": [],
    }

    # Download transcripts for each video with progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            "[cyan]Downloading transcripts...", 
            total=len(video_ids)
        )

        for video_id in video_ids:
            file_path = output_path / f"{video_id}.md"
            metadata = video_metadata.get(video_id, {})
            video_title = metadata.get("title", video_id) if metadata else video_id

            # Skip if file already exists
            if skip_existing and file_path.exists():
                progress.update(
                    task, 
                    description=f"[yellow]⏭  Skipping [bold]{video_title[:50]}[/bold]... (already exists)[/yellow]"
                )
                stats["skipped"] += 1
                progress.advance(task)
                continue

            progress.update(
                task, 
                description=f"[cyan]📥 Downloading transcript for [bold]{video_title[:50]}[/bold]...[/cyan]"
            )
            transcript_text = download_transcript(video_id, languages=languages)

            # Add delay after transcript download to avoid rate limiting
            time.sleep(transcript_delay)

            if transcript_text:
                save_transcript(video_id, transcript_text, output_dir, metadata=metadata)
                stats["downloaded"] += 1
                progress.update(
                    task,
                    description=f"[green]✓ Saved transcript for [bold]{video_title[:50]}[/bold][/green]"
                )
            else:
                stats["failed"] += 1
                stats["failed_videos"].append(video_id)
                progress.update(
                    task,
                    description=f"[red]✗ Failed to download transcript for [bold]{video_title[:50]}[/bold][/red]"
                )

            progress.advance(task)

    # Print summary
    console.print("\n")
    summary_table = Table(title="Download Summary", show_header=True, header_style="bold magenta")
    summary_table.add_column("Metric", style="cyan", no_wrap=True)
    summary_table.add_column("Count", style="green", justify="right")
    
    summary_table.add_row("Total Videos", str(stats["total_videos"]))
    summary_table.add_row("Downloaded", f"[green]{stats['downloaded']}[/green]")
    summary_table.add_row("Skipped", f"[yellow]{stats['skipped']}[/yellow]")
    summary_table.add_row("Failed", f"[red]{stats['failed']}[/red]")
    
    console.print(summary_table)
    
    if stats["failed_videos"]:
        failed_list = []
        for video_id in stats["failed_videos"]:
            metadata = video_metadata.get(video_id, {})
            title = metadata.get("title", video_id) if metadata else video_id
            failed_list.append(f"{title} ({video_id})")
        console.print(f"\n[red]Failed videos:[/red]")
        for item in failed_list:
            console.print(f"  • {item}")

    return stats
