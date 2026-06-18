"""DataUpdateCoordinators for YouTube Channel Latest."""
from __future__ import annotations

import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.dt import utcnow

from .const import (
    CONF_CHANNELS,
    CONF_ENTRY_TYPE,
    CONF_MAX_VIDEOS,
    DEFAULT_MAX_VIDEOS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    ENTRY_TYPE_CHANNEL,
    YOUTUBE_CHANNEL_SEARCH,
    YOUTUBE_RSS_URL,
)

_LOGGER = logging.getLogger(__name__)

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}

_RSS_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml",
    "Accept-Language": "en-US,en;q=0.9",
}

_YOUTUBE_SHORTS_URL = "https://www.youtube.com/shorts/{video_id}"


# ---------------------------------------------------------------------------
# Channel coordinator
# ---------------------------------------------------------------------------

class YouTubeCoordinator(DataUpdateCoordinator):
    """Fetch latest videos for all configured YouTube channels."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._entry = entry
        self.last_update_success_time: datetime | None = None
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_channel",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict:
        channels: list[str] = self._entry.data.get(CONF_CHANNELS, [])

        result: dict[str, dict] = {}
        # SOCS cookie bypasses YouTube's GDPR consent page (common for EU channels)
        async with aiohttp.ClientSession(cookies={"SOCS": "CAI"}) as session:
            for channel in channels:
                result[channel] = await self._fetch_channel_data(session, channel)
        self.last_update_success_time = utcnow()
        return result

    async def async_refresh_channel(self, channel: str) -> None:
        """Refresh one configured channel and notify entities."""
        result = dict(self.data or {})
        # SOCS cookie bypasses YouTube's GDPR consent page (common for EU channels)
        async with aiohttp.ClientSession(cookies={"SOCS": "CAI"}) as session:
            result[channel] = await self._fetch_channel_data(session, channel)
        self.last_update_success_time = utcnow()
        self.async_set_updated_data(result)

    async def _fetch_channel_data(self, session: aiohttp.ClientSession, channel: str) -> dict:
        max_videos: int = self._entry.options.get(
            CONF_MAX_VIDEOS, self._entry.data.get(CONF_MAX_VIDEOS, DEFAULT_MAX_VIDEOS)
        )

        try:
            channel_id, channel_name = await self._resolve_channel(session, channel)
            videos = await self._fetch_videos(session, channel_id, max_videos)
            videos = await self._filter_regular_videos(session, videos)
            return {
                "channel_id": channel_id,
                "channel_name": channel_name,
                "channel_handle": channel if channel.startswith("@") else f"@{channel_name}",
                "channel_url": f"https://www.youtube.com/channel/{channel_id}",
                "rss_url": YOUTUBE_RSS_URL.format(channel_id=channel_id),
                "videos": videos,
            }
        except Exception as err:
            _LOGGER.warning("Error fetching channel '%s': %s", channel, err)
            return {
                "channel_id": None,
                "channel_name": channel,
                "channel_handle": channel if channel.startswith("@") else None,
                "channel_url": None,
                "rss_url": None,
                "videos": [],
            }

    async def _resolve_channel(self, session: aiohttp.ClientSession, channel: str) -> tuple[str, str]:
        channel = channel.strip()
        if re.match(r"^UC[\w-]{22}$", channel):
            name = await self._fetch_channel_name(session, channel)
            return channel, name or channel

        handle = channel.lstrip("@")
        url = YOUTUBE_CHANNEL_SEARCH.format(handle=handle)
        async with session.get(url, allow_redirects=True, headers=_HEADERS) as resp:
            final_url = str(resp.url)
            html = await resp.text()

        # Fastest path: YouTube may redirect @handle → /channel/UCxxx
        match = re.search(r'/channel/(UC[\w-]{22})', final_url)

        if not match:
            for pattern in (
                r'<link[^>]+type="application/rss\+xml"[^>]+href="[^"]*channel_id=(UC[\w-]{22})"',
                r'href="[^"]*channel_id=(UC[\w-]{22})"',
                r'"channelId":"(UC[\w-]{22})"',
                r'"externalId":"(UC[\w-]{22})"',
                r'"browseId":"(UC[\w-]{22})"',
                r'youtube\.com/channel/(UC[\w-]{22})',
                r'"id":"(UC[\w-]{22})"',
            ):
                match = re.search(pattern, html)
                if match:
                    break

        if not match:
            raise UpdateFailed(f"Cannot resolve channel ID for '{channel}'")

        channel_id = match.group(1)
        name_match = re.search(r'<meta name="title" content="([^"]+)"', html)
        if not name_match:
            name_match = re.search(r'"title":"([^"]+)","canonicalBaseUrl":"/@', html)
        channel_name = name_match.group(1) if name_match else f"@{handle}"
        return channel_id, channel_name

    async def _fetch_channel_name(self, session: aiohttp.ClientSession, channel_id: str) -> str | None:
        url = YOUTUBE_RSS_URL.format(channel_id=channel_id)
        async with session.get(url, headers=_RSS_HEADERS) as resp:
            if resp.status != 200:
                return None
            xml_text = await resp.text()
        root = ET.fromstring(xml_text)
        title_el = root.find("atom:title", NS)
        return title_el.text if title_el is not None else None

    async def _fetch_videos(self, session: aiohttp.ClientSession, channel_id: str, max_videos: int) -> list[dict]:
        url = YOUTUBE_RSS_URL.format(channel_id=channel_id)
        async with session.get(url, headers=_RSS_HEADERS) as resp:
            if resp.status != 200:
                raise UpdateFailed(f"RSS fetch failed ({resp.status})")
            xml_text = await resp.text()

        root = ET.fromstring(xml_text)
        videos: list[dict] = []
        for entry in root.findall("atom:entry", NS)[:max_videos]:
            video_id_el = entry.find("yt:videoId", NS)
            title_el = entry.find("atom:title", NS)
            published_el = entry.find("atom:published", NS)
            updated_el = entry.find("atom:updated", NS)
            link_el = entry.find("atom:link", NS)
            group_el = entry.find("media:group", NS)

            description, thumbnail = "", ""
            if group_el is not None:
                desc_el = group_el.find("media:description", NS)
                thumb_el = group_el.find("media:thumbnail", NS)
                description = desc_el.text if desc_el is not None else ""
                thumbnail = thumb_el.get("url", "") if thumb_el is not None else ""

            videos.append({
                "video_id": video_id_el.text if video_id_el is not None else "",
                "title": title_el.text if title_el is not None else "",
                "description": description,
                "thumbnail": thumbnail,
                "url": link_el.get("href", "") if link_el is not None else "",
                "published": published_el.text if published_el is not None else "",
                "updated": updated_el.text if updated_el is not None else "",
            })
        return videos

    async def _filter_regular_videos(self, session: aiohttp.ClientSession, videos: list[dict]) -> list[dict]:
        async def is_regular_video(video: dict) -> bool:
            url = _YOUTUBE_SHORTS_URL.format(video_id=video["video_id"])
            try:
                async with session.head(
                    url, allow_redirects=False, headers=_HEADERS,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    return resp.status != 200
            except Exception:
                return True

        checks = await asyncio.gather(*[is_regular_video(v) for v in videos])
        return [video for video, is_regular in zip(videos, checks) if is_regular]


# ---------------------------------------------------------------------------
# Latest (cross-channel) coordinator
# ---------------------------------------------------------------------------

class YouTubeLatestCoordinator(DataUpdateCoordinator):
    """Aggregate latest videos across all channel coordinators."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._entry = entry
        self.last_update_success_time: datetime | None = None
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_latest",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict:
        all_videos: list[dict] = []

        for entry_id, coordinator in self.hass.data.get(DOMAIN, {}).items():
            if entry_id == self._entry.entry_id:
                continue
            if not isinstance(coordinator, YouTubeCoordinator):
                continue
            if coordinator.data is None:
                continue
            for channel_data in coordinator.data.values():
                for video in channel_data.get("videos", []):
                    all_videos.append({**video, "channel_name": channel_data.get("channel_name", "")})

        all_videos.sort(key=lambda v: v.get("published", ""), reverse=True)
        self.last_update_success_time = utcnow()
        return {"videos": all_videos}
