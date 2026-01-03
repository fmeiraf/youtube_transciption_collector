# YouTube Transcript Collector

A lightweight Python package for downloading YouTube channel transcripts with ease.

## Installation

```bash
# Using uv (recommended) - installs all dependencies including Jupyter support
uv sync --all-groups

# Or using pip
pip install -e .
pip install ipykernel ipywidgets  # For Jupyter notebook support
```

**Note**: After installation, restart your Jupyter kernel if you're using notebooks.

## Setup

Create a `.env` file in your project root:

```bash
YOUTUBE_API_KEY=your_youtube_api_key_here
```

Get your YouTube Data API v3 key from [Google Cloud Console](https://console.cloud.google.com/).

## Usage

### Quick Start - Download All Transcripts from a Channel

```python
from youtube_transcript_collector import (
    get_channel_id,
    download_channel_transcripts,
    load_config_from_env,
)

# Load API key from .env
api_key = load_config_from_env()

# Get channel ID from URL or handle
channel_id = get_channel_id("https://www.youtube.com/@starterstory", api_key)

# Download all transcripts
stats = download_channel_transcripts(
    channel_id=channel_id,
    api_key=api_key,
    output_dir="transcriptions",
    max_videos=10,  # Limit to 10 videos, or None for all
    languages=["en"],  # Prefer English, or None for any language
    skip_existing=True
)

print(f"Downloaded: {stats['downloaded']}, Failed: {stats['failed']}")
```

### Composable API - Build Your Own Workflow

```python
from youtube_transcript_collector import (
    get_channel_id,
    get_all_video_ids,
    get_video_metadata,
    download_transcript,
    save_transcript,
    load_config_from_env,
)

# Load configuration
api_key = load_config_from_env()

# Get channel ID (supports handles, URLs, or channel IDs)
channel_id = get_channel_id("@channelname", api_key)

# Get all video IDs from the channel
video_ids = get_all_video_ids(
    channel_id,
    api_key,
    max_results=50  # Limit to 50 videos
)

# Get metadata for videos
metadata = get_video_metadata(video_ids, api_key)

# Download transcripts individually
for video_id in video_ids:
    transcript = download_transcript(video_id, languages=["en"])
    if transcript:
        save_transcript(
            video_id,
            transcript,
            output_dir="transcriptions",
            metadata=metadata.get(video_id)
        )
```

## API Reference

### Configuration

- **`load_config_from_env()`** - Load YouTube API key from `.env` file

### Channel & Video API

- **`get_channel_id(identifier, api_key, delay=1.0)`** - Get channel ID from URL, handle (@username), or username
- **`get_all_video_ids(channel_id, api_key, max_results=None, api_delay=1.0)`** - Get all video IDs from a channel
- **`get_video_metadata(video_ids, api_key, api_delay=1.0)`** - Get metadata (title, description, views, etc.) for videos

### Transcript Functions

- **`download_transcript(video_id, languages=None)`** - Download transcript for a single video
- **`save_transcript(video_id, transcript_text, output_dir="transcriptions", metadata=None)`** - Save transcript to markdown file
- **`download_channel_transcripts(channel_id, api_key, ...)`** - Download all transcripts from a channel (high-level function)

## Features

- ✨ Simple, composable API
- 🔄 Automatic rate limiting with configurable delays
- 📊 Rich progress bars and summaries
- 📝 Saves transcripts as markdown with metadata
- ⏭️ Skip already downloaded transcripts
- 🌍 Multi-language support
- 🎯 Multiple channel identifier formats (URL, handle, username, channel ID)

## Output Format

Transcripts are saved as markdown files with the following structure:

```markdown
# Video Title

**Video ID:** abc123xyz
**Video URL:** https://www.youtube.com/watch?v=abc123xyz
**Channel:** Channel Name
**Published:** 2024-01-01T00:00:00Z
**Duration:** PT10M30S
**Views:** 10000

## Description

Video description here...

---

## Transcript

Transcript text here...
```

## Development

```bash
# Install with dev dependencies
uv sync --group dev

# Run in Jupyter
jupyter notebook starter_story.ipynb
```

## License

MIT
