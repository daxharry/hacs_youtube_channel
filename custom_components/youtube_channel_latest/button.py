"""Button platform for YouTube Channel Latest."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ENTRY_TYPE, DOMAIN, ENTRY_TYPE_LATEST, ICON
from .coordinator import YouTubeCoordinator, YouTubeLatestCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    if entry.data.get(CONF_ENTRY_TYPE) != ENTRY_TYPE_LATEST:
        return
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([RefreshAllButton(coordinator)])


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
