"""YouTube Data API functions for retrieving channel and video information."""

import time
from typing import Dict, List, Optional

import requests


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
        ValueError: If the uploads playlist ID cannot be found
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
        Dictionary mapping video_id to metadata dict with keys:
        - title
        - description
        - publishedAt
        - channelTitle
        - duration
        - viewCount
        - likeCount
    """
    metadata = {}

    # YouTube API allows up to 50 video IDs per request
    batch_size = 50
    url = "https://www.googleapis.com/youtube/v3/videos"

    for i in range(0, len(video_ids), batch_size):
        batch = video_ids[i : i + batch_size]

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
