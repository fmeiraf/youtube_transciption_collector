"""Configuration utilities for loading API keys and settings."""

import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def load_config_from_env() -> str:
    """
    Load YouTube API key from environment variables (.env file).

    Returns:
        YouTube API key

    Raises:
        ValueError: If YOUTUBE_API_KEY is not set
    """
    api_key = os.getenv("YOUTUBE_API_KEY")

    if not api_key:
        raise ValueError(
            "YOUTUBE_API_KEY not found in environment variables. "
            "Please set it in your .env file or as an environment variable."
        )

    return api_key
