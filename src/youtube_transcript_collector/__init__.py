"""YouTube Transcript Collector - A tool for downloading YouTube channel transcripts."""

__version__ = "0.1.0"

from .utils import (
    download_channel_transcripts,
    load_config_from_env,
)

__all__ = [
    "download_channel_transcripts",
    "load_config_from_env",
]

