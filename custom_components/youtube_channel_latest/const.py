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
CONF_EXCLUDE_SHORTS = "exclude_shorts"
CONF_LATEST_COUNT = "latest_count"

DEFAULT_MAX_VIDEOS = 10
DEFAULT_LATEST_COUNT = 10
DEFAULT_EXCLUDE_SHORTS = False
DEFAULT_SCAN_INTERVAL = 3600  # seconds

YOUTUBE_RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
YOUTUBE_CHANNEL_SEARCH = "https://www.youtube.com/@{handle}"
YOUTUBE_SHORTS_URL = "https://www.youtube.com/shorts/{video_id}"
