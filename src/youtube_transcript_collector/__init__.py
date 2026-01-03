"""YouTube Transcript Collector - A tool for downloading YouTube channel transcripts."""

__version__ = "0.1.0"

# Main workflow function
from .transcript import download_channel_transcripts

# API functions for getting channel and video data
from .api import (
    get_channel_id,
    get_all_video_ids,
    get_video_metadata,
)

# Transcript functions
from .transcript import (
    download_transcript,
    save_transcript,
)

# Configuration
from .config import load_config_from_env

__all__ = [
    # Main workflow
    "download_channel_transcripts",
    # API functions
    "get_channel_id",
    "get_all_video_ids",
    "get_video_metadata",
    # Transcript functions
    "download_transcript",
    "save_transcript",
    # Config
    "load_config_from_env",
]

