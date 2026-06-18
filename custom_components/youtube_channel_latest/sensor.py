"""Sensor platform for YouTube Channel Latest."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_CHANNELS,
    CONF_ENTRY_TYPE,
    CONF_EXCLUDE_SHORTS,
    CONF_LATEST_COUNT,
    CONF_MAX_VIDEOS,
    DEFAULT_LATEST_COUNT,
    DEFAULT_MAX_VIDEOS,
    DOMAIN,
    ENTRY_TYPE_LATEST,
)
from .coordinator import YouTubeCoordinator, YouTubeLatestCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entry_type = entry.data.get(CONF_ENTRY_TYPE, "channel")

    if entry_type == ENTRY_TYPE_LATEST:
        _setup_latest_entry(entry, coordinator, async_add_entities)
    else:
        _setup_channel_entry(entry, coordinator, async_add_entities)


def _setup_channel_entry(
    entry: ConfigEntry,
    coordinator: YouTubeCoordinator,
    async_add_entities: AddEntitiesCallback,
) -> None:
    channels: list[str] = entry.data.get(CONF_CHANNELS, [])
    max_videos: int = entry.options.get(CONF_MAX_VIDEOS, entry.data.get(CONF_MAX_VIDEOS, DEFAULT_MAX_VIDEOS))
    exclude_shorts: bool = entry.options.get(CONF_EXCLUDE_SHORTS, entry.data.get(CONF_EXCLUDE_SHORTS, False))

    entities: list[SensorEntity] = []
    for channel in channels:
        slug = channel.lstrip("@").replace(" ", "_").lower()
        entities.append(ChannelRefreshSensor(coordinator, channel, slug))
        entities.append(ChannelStatusSensor(coordinator, channel, slug))
        entities.append(ChannelInfoSensor(coordinator, channel, slug, "channel_url",    "channel_url",    "Channel URL",    "mdi:web"))
        entities.append(ChannelInfoSensor(coordinator, channel, slug, "channel_handle", "channel_handle", "Channel Handle", "mdi:at"))
        entities.append(ChannelInfoSensor(coordinator, channel, slug, "channel_id",     "channel_id",     "Channel ID",     "mdi:identifier"))
        entities.append(ChannelInfoSensor(coordinator, channel, slug, "rss_url",        "rss_url",        "RSS URL",        "mdi:rss"))
        for i in range(1, max_videos + 1):
            entities.append(VideoSlotSensor(coordinator, channel, slug, i, is_short=False))
        if not exclude_shorts:
            for i in range(1, max_videos + 1):
                entities.append(VideoSlotSensor(coordinator, channel, slug, i, is_short=True))

    async_add_entities(entities)


def _setup_latest_entry(
    entry: ConfigEntry,
    coordinator: YouTubeLatestCoordinator,
    async_add_entities: AddEntitiesCallback,
) -> None:
    count: int = entry.options.get(CONF_LATEST_COUNT, entry.data.get(CONF_LATEST_COUNT, DEFAULT_LATEST_COUNT))

    entities: list[SensorEntity] = [
        LatestRefreshSensor(coordinator),
        LatestStatusSensor(coordinator),
    ]
    for i in range(1, count + 1):
        entities.append(LatestVideoSensor(coordinator, i))

    async_add_entities(entities)


# ---------------------------------------------------------------------------
# Channel sensors
# ---------------------------------------------------------------------------

class ChannelInfoSensor(CoordinatorEntity, SensorEntity):
    """Static info sensor for a channel (URL, handle, channel ID, RSS URL)."""

    def __init__(
        self,
        coordinator: YouTubeCoordinator,
        channel: str,
        slug: str,
        data_key: str,
        unique_suffix: str,
        name_suffix: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator)
        self._channel = channel
        self._data_key = data_key
        self._name_suffix = name_suffix
        self._attr_unique_id = f"youtube_{slug}_{unique_suffix}"
        self._attr_icon = icon

    @property
    def name(self) -> str:
        cname = self.coordinator.data.get(self._channel, {}).get("channel_name") or self._channel
        return f"YouTube {cname} {self._name_suffix}"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get(self._channel, {}).get(self._data_key)


class ChannelRefreshSensor(CoordinatorEntity, SensorEntity):
    """Last refresh timestamp for a channel."""

    _attr_icon = "mdi:clock-outline"
    _attr_device_class = "timestamp"

    def __init__(self, coordinator: YouTubeCoordinator, channel: str, slug: str) -> None:
        super().__init__(coordinator)
        self._channel = channel
        self._attr_unique_id = f"youtube_{slug}_last_refresh"

    @property
    def name(self) -> str:
        name = self.coordinator.data.get(self._channel, {}).get("channel_name") or self._channel
        return f"YouTube {name} Last Refresh"

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.last_update_success_time


class ChannelStatusSensor(CoordinatorEntity, SensorEntity):
    """Fetch status for a channel (OK / error)."""

    _attr_icon = "mdi:check-circle-outline"

    def __init__(self, coordinator: YouTubeCoordinator, channel: str, slug: str) -> None:
        super().__init__(coordinator)
        self._channel = channel
        self._attr_unique_id = f"youtube_{slug}_status"

    @property
    def name(self) -> str:
        name = self.coordinator.data.get(self._channel, {}).get("channel_name") or self._channel
        return f"YouTube {name} Status"

    @property
    def native_value(self) -> str:
        if not self.coordinator.last_update_success:
            return "error"
        data = self.coordinator.data.get(self._channel, {})
        return "ok" if data.get("channel_id") else "error"

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data.get(self._channel, {})
        return {
            "channel_id": data.get("channel_id"),
            "channel_name": data.get("channel_name"),
            "video_count": len(data.get("videos", [])),
            "short_count": len(data.get("shorts", [])),
        }


class VideoSlotSensor(CoordinatorEntity, SensorEntity):
    """One sensor per video/short slot."""

    def __init__(
        self,
        coordinator: YouTubeCoordinator,
        channel: str,
        slug: str,
        position: int,
        is_short: bool,
    ) -> None:
        super().__init__(coordinator)
        self._channel = channel
        self._position = position
        self._is_short = is_short
        kind = "short" if is_short else "video"
        self._attr_unique_id = f"youtube_{slug}_{kind}_{position:02d}"
        self._attr_icon = "mdi:youtube-shorts" if is_short else "mdi:youtube"

    @property
    def _channel_name(self) -> str:
        return self.coordinator.data.get(self._channel, {}).get("channel_name") or self._channel

    @property
    def name(self) -> str:
        kind = "Short" if self._is_short else "Video"
        return f"YouTube {self._channel_name} {kind} {self._position:02d}"

    @property
    def _video(self) -> dict | None:
        data = self.coordinator.data.get(self._channel, {})
        lst = data.get("shorts" if self._is_short else "videos", [])
        idx = self._position - 1
        return lst[idx] if idx < len(lst) else None

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._video is not None

    @property
    def native_value(self) -> str | None:
        v = self._video
        return v["title"] if v else None

    @property
    def extra_state_attributes(self) -> dict:
        v = self._video
        if not v:
            return {}
        return {
            "video_id": v.get("video_id"),
            "url": v.get("url"),
            "thumbnail": v.get("thumbnail"),
            "description": v.get("description"),
            "published": v.get("published"),
            "updated": v.get("updated"),
        }


# ---------------------------------------------------------------------------
# Latest (cross-channel) sensors
# ---------------------------------------------------------------------------

class LatestRefreshSensor(CoordinatorEntity, SensorEntity):
    """Last refresh timestamp for the Latest feed."""

    _attr_unique_id = "youtube_latest_last_refresh"
    _attr_name = "YouTube Latest Last Refresh"
    _attr_icon = "mdi:clock-outline"
    _attr_device_class = "timestamp"

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.last_update_success_time


class LatestStatusSensor(CoordinatorEntity, SensorEntity):
    """Status sensor for the Latest feed."""

    _attr_unique_id = "youtube_latest_status"
    _attr_name = "YouTube Latest Status"
    _attr_icon = "mdi:check-circle-outline"

    @property
    def native_value(self) -> str:
        return "ok" if self.coordinator.last_update_success else "error"

    @property
    def extra_state_attributes(self) -> dict:
        videos = self.coordinator.data.get("videos", []) if self.coordinator.data else []
        return {"total_videos": len(videos)}


class LatestVideoSensor(CoordinatorEntity, SensorEntity):
    """One sensor per slot in the cross-channel latest feed."""

    _attr_icon = "mdi:youtube"

    def __init__(self, coordinator: YouTubeLatestCoordinator, position: int) -> None:
        super().__init__(coordinator)
        self._position = position
        self._attr_unique_id = f"youtube_latest_video_{position:02d}"
        self._attr_name = f"YouTube Latest Video {position:02d}"

    @property
    def _video(self) -> dict | None:
        if not self.coordinator.data:
            return None
        videos = self.coordinator.data.get("videos", [])
        idx = self._position - 1
        return videos[idx] if idx < len(videos) else None

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._video is not None

    @property
    def native_value(self) -> str | None:
        v = self._video
        if not v:
            return None
        channel = v.get("channel_name") or ""
        handle = f"@{channel}" if channel and not channel.startswith("@") else channel
        return f"{handle} : {v['title']}" if handle else v["title"]

    @property
    def extra_state_attributes(self) -> dict:
        v = self._video
        if not v:
            return {}
        return {
            "channel_name": v.get("channel_name"),
            "video_id": v.get("video_id"),
            "url": v.get("url"),
            "thumbnail": v.get("thumbnail"),
            "description": v.get("description"),
            "published": v.get("published"),
            "updated": v.get("updated"),
            "is_short": v.get("is_short"),
        }
