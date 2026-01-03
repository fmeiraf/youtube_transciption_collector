"""Functions for downloading and saving YouTube transcripts."""

import time
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from youtube_transcript_api import YouTubeTranscriptApi

from .api import get_all_video_ids, get_video_metadata

console = Console()


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
        transcript_text = "\n".join([entry.text for entry in transcript])
        return transcript_text
    except Exception as e:
        console.print(
            f"[red]Error downloading transcript for video {video_id}: {e}[/red]"
        )
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
        Dictionary with statistics about the download process:
        - total_videos: Total number of videos found
        - downloaded: Number of transcripts successfully downloaded
        - skipped: Number of videos skipped (already exists)
        - failed: Number of failed downloads
        - failed_videos: List of video IDs that failed to download
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Get all video IDs
    console.print(
        f"[cyan]🔍 Fetching video IDs for channel [bold]{channel_id}[/bold]...[/cyan]"
    )
    video_ids = get_all_video_ids(
        channel_id, api_key, max_results=max_videos, api_delay=api_delay
    )
    console.print(f"[green]✓ Found [bold]{len(video_ids)}[/bold] videos[/green]\n")

    # Fetch video metadata
    console.print("[cyan]📋 Fetching video metadata...[/cyan]")
    video_metadata = get_video_metadata(video_ids, api_key, api_delay=api_delay)
    console.print(
        f"[green]✓ Retrieved metadata for [bold]{len(video_metadata)}[/bold] videos[/green]\n"
    )

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
            "[cyan]Downloading transcripts...", total=len(video_ids)
        )

        for video_id in video_ids:
            file_path = output_path / f"{video_id}.md"
            metadata = video_metadata.get(video_id, {})
            video_title = metadata.get("title", video_id) if metadata else video_id

            # Skip if file already exists
            if skip_existing and file_path.exists():
                progress.update(
                    task,
                    description=f"[yellow]⏭  Skipping [bold]{video_title[:50]}[/bold]... (already exists)[/yellow]",
                )
                stats["skipped"] += 1
                progress.advance(task)
                continue

            progress.update(
                task,
                description=f"[cyan]📥 Downloading transcript for [bold]{video_title[:50]}[/bold]...[/cyan]",
            )
            transcript_text = download_transcript(video_id, languages=languages)

            # Add delay after transcript download to avoid rate limiting
            time.sleep(transcript_delay)

            if transcript_text:
                save_transcript(
                    video_id, transcript_text, output_dir, metadata=metadata
                )
                stats["downloaded"] += 1
                progress.update(
                    task,
                    description=f"[green]✓ Saved transcript for [bold]{video_title[:50]}[/bold][/green]",
                )
            else:
                stats["failed"] += 1
                stats["failed_videos"].append(video_id)
                progress.update(
                    task,
                    description=f"[red]✗ Failed to download transcript for [bold]{video_title[:50]}[/bold][/red]",
                )

            progress.advance(task)

    # Print summary
    console.print("\n")
    summary_table = Table(
        title="Download Summary", show_header=True, header_style="bold magenta"
    )
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
        console.print("\n[red]Failed videos:[/red]")
        for item in failed_list:
            console.print(f"  • {item}")

    return stats
