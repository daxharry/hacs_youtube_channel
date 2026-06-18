"""YouTube Channel Latest - HACS Integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_ENTRY_TYPE, DOMAIN, ENTRY_TYPE_LATEST, PLATFORMS
from .coordinator import YouTubeCoordinator, YouTubeLatestCoordinator

_LEGACY_EXCLUDE_SHORTS = "exclude_shorts"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    entry_type = entry.data.get(CONF_ENTRY_TYPE, "channel")

    if entry_type == ENTRY_TYPE_LATEST:
        coordinator = YouTubeLatestCoordinator(hass, entry)
    else:
        coordinator = YouTubeCoordinator(hass, entry)

    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove legacy Shorts option from existing config entries."""
    data = dict(entry.data)
    options = dict(entry.options)
    changed = False

    if _LEGACY_EXCLUDE_SHORTS in data:
        data.pop(_LEGACY_EXCLUDE_SHORTS)
        changed = True

    if _LEGACY_EXCLUDE_SHORTS in options:
        options.pop(_LEGACY_EXCLUDE_SHORTS)
        changed = True

    if changed:
        hass.config_entries.async_update_entry(entry, data=data, options=options)

    return True
