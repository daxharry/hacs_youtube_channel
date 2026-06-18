"""Button platform for YouTube Channel Latest."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_CHANNELS, CONF_ENTRY_TYPE, DOMAIN, ENTRY_TYPE_LATEST, ICON
from .coordinator import YouTubeCoordinator, YouTubeLatestCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_LATEST:
        async_add_entities([RefreshAllButton(coordinator)])
        return

    channels: list[str] = entry.data.get(CONF_CHANNELS, [])
    async_add_entities(
        [
            RefreshChannelButton(
                coordinator,
                channel,
                channel.lstrip("@").replace(" ", "_").lower(),
            )
            for channel in channels
        ]
    )


def _channel_device_info(coordinator: YouTubeCoordinator, channel: str) -> dict:
    data = coordinator.data.get(channel, {}) if coordinator.data else {}
    channel_id = data.get("channel_id") or channel
    channel_name = data.get("channel_name") or channel
    device_info = {
        "identifiers": {(DOMAIN, channel_id)},
        "name": f"YouTube {channel_name}",
        "manufacturer": "YouTube",
        "model": "Channel RSS feed",
        "entry_type": DeviceEntryType.SERVICE,
    }
    if channel_url := data.get("channel_url"):
        device_info["configuration_url"] = channel_url
    return device_info


class RefreshChannelButton(ButtonEntity):
    """Button that refreshes one configured channel."""

    _attr_icon = ICON

    def __init__(self, coordinator: YouTubeCoordinator, channel: str, slug: str) -> None:
        super().__init__()
        self._coordinator = coordinator
        self._channel = channel
        self._attr_unique_id = f"youtube_{slug}_refresh"

    @property
    def name(self) -> str:
        data = self._coordinator.data.get(self._channel, {}) if self._coordinator.data else {}
        channel_name = data.get("channel_name") or self._channel
        return f"YouTube {channel_name} Refresh"

    @property
    def device_info(self) -> dict:
        return _channel_device_info(self._coordinator, self._channel)

    async def async_press(self) -> None:
        await self._coordinator.async_refresh_channel(self._channel)


class RefreshAllButton(ButtonEntity):
    """Button that refreshes all channel coordinators then the Latest feed."""

    _attr_unique_id = "youtube_latest_refresh_all"
    _attr_name = "YouTube Latest Refresh All Channels"
    _attr_icon = ICON

    def __init__(self, coordinator: YouTubeLatestCoordinator) -> None:
        super().__init__()
        self._coordinator = coordinator

    @property
    def device_info(self) -> dict:
        return {
            "identifiers": {(DOMAIN, "latest")},
            "name": "YouTube Latest",
            "manufacturer": "YouTube",
            "model": "Aggregated latest feed",
            "entry_type": DeviceEntryType.SERVICE,
        }

    async def async_press(self) -> None:
        for coord in self.hass.data.get(DOMAIN, {}).values():
            if isinstance(coord, YouTubeCoordinator):
                await coord.async_request_refresh()
        await self._coordinator.async_request_refresh()
