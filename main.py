"""Main entry point for the YouTube transcript collector."""
from youtube_transcript_collector.utils import download_channel_transcripts, load_config_from_env


def main():
    """
    Example usage of the YouTube channel transcript downloader.
    
    Set the following environment variables in .env file:
    - YOUTUBE_API_KEY: Your YouTube Data API v3 key
    - YOUTUBE_CHANNEL_ID: The channel ID to download transcripts from
    """
    try:
        api_key, channel_id = load_config_from_env()
    except ValueError as e:
        print(f"Error: {e}")
        print("\nMake sure your .env file contains:")
        print("YOUTUBE_API_KEY=your_api_key_here")
        print("YOUTUBE_CHANNEL_ID=your_channel_id_here")
        return
    
    print(f"Starting transcript download for channel: {channel_id}")
    print("-" * 60)
    
    # Download transcripts
    stats = download_channel_transcripts(
        channel_id=channel_id,
        api_key=api_key,
        output_dir="transcriptions",
        max_videos=None,  # Set to a number to limit downloads, None for all
        languages=None,  # Set to ['en'] to prefer English, None for any language
        skip_existing=True
    )
    
    # Print summary
    print("-" * 60)
    print("Download Summary:")
    print(f"  Total videos: {stats['total_videos']}")
    print(f"  Downloaded: {stats['downloaded']}")
    print(f"  Skipped: {stats['skipped']}")
    print(f"  Failed: {stats['failed']}")
    
    if stats['failed_videos']:
        print(f"\nFailed video IDs: {', '.join(stats['failed_videos'])}")


if __name__ == "__main__":
    main()
