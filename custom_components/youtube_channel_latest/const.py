"""Constants for YouTube Channel Latest."""

DOMAIN = "youtube_channel_latest"
PLATFORMS = ["sensor", "button"]
NAME = "YouTube Channel Latest"
ICON = "mdi:youtube"

# Entry types
ENTRY_TYPE_CHANNEL = "channel"
ENTRY_TYPE_LATEST = "latest"

CONF_ENTRY_TYPE = "entry_type"
CONF_CHANNELS = "channels"
CONF_MAX_VIDEOS = "max_videos"
CONF_LATEST_COUNT = "latest_count"

DEFAULT_MAX_VIDEOS = 10
DEFAULT_LATEST_COUNT = 10
DEFAULT_SCAN_INTERVAL = 3600  # seconds

YOUTUBE_RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
YOUTUBE_RSS_PLAYLIST_URL = "https://www.youtube.com/feeds/videos.xml?playlist_id={playlist_id}"
YOUTUBE_CHANNEL_SEARCH = "https://www.youtube.com/@{handle}"


def channel_videos_only_playlist_id(channel_id: str) -> str:
    """Return the UULF playlist ID whose RSS feed excludes Shorts."""
    if not channel_id.startswith("UC") or len(channel_id) != 24:
        raise ValueError(f"Invalid YouTube channel ID: {channel_id}")
    return f"UULF{channel_id[2:]}"


def channel_videos_only_rss_url(channel_id: str) -> str:
    """RSS feed URL for regular uploads only (no Shorts)."""
    return YOUTUBE_RSS_PLAYLIST_URL.format(
        playlist_id=channel_videos_only_playlist_id(channel_id)
    )
