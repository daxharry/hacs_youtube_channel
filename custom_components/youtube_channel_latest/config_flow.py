"""Config flow for YouTube Channel Latest."""
from __future__ import annotations

import re

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_CHANNELS,
    CONF_ENTRY_TYPE,
    CONF_EXCLUDE_SHORTS,
    CONF_LATEST_COUNT,
    CONF_MAX_VIDEOS,
    DEFAULT_EXCLUDE_SHORTS,
    DEFAULT_LATEST_COUNT,
    DEFAULT_MAX_VIDEOS,
    DOMAIN,
    ENTRY_TYPE_CHANNEL,
    ENTRY_TYPE_LATEST,
)


def _has_latest_entry(hass) -> bool:
    return any(
        e.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_LATEST
        for e in hass.config_entries.async_entries(DOMAIN)
    )


def _parse_channels(raw: str) -> list[str]:
    return [c.strip() for c in re.split(r"[,\n]+", raw) if c.strip()]


def _title_from_channels(channels: list[str]) -> str:
    labels = [c if c.startswith("@") else f"@{c}" for c in channels[:3]]
    title = "YouTube " + ", ".join(labels)
    if len(channels) > 3:
        title += f" +{len(channels) - 3}"
    return title


class YouTubeChannelLatestConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for YouTube Channel Latest."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        return await self.async_step_channel()

    # ------------------------------------------------------------------
    # Channel entry
    # ------------------------------------------------------------------

    async def async_step_channel(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            channels = _parse_channels(user_input[CONF_CHANNELS])
            if not channels:
                errors[CONF_CHANNELS] = "no_channels"
            else:
                if not _has_latest_entry(self.hass):
                    self.hass.async_create_task(
                        self.hass.config_entries.flow.async_init(
                            DOMAIN,
                            context={"source": config_entries.SOURCE_IMPORT},
                            data={CONF_LATEST_COUNT: DEFAULT_LATEST_COUNT},
                        )
                    )
                return self.async_create_entry(
                    title=_title_from_channels(channels),
                    data={
                        CONF_ENTRY_TYPE: ENTRY_TYPE_CHANNEL,
                        CONF_CHANNELS: channels,
                        CONF_MAX_VIDEOS: user_input[CONF_MAX_VIDEOS],
                        CONF_EXCLUDE_SHORTS: user_input[CONF_EXCLUDE_SHORTS],
                    },
                )

        return self.async_show_form(
            step_id="channel",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CHANNELS): str,
                    vol.Optional(CONF_MAX_VIDEOS, default=DEFAULT_MAX_VIDEOS): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=50)
                    ),
                    vol.Optional(CONF_EXCLUDE_SHORTS, default=DEFAULT_EXCLUDE_SHORTS): bool,
                }
            ),
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Auto-created Latest entry (via SOURCE_IMPORT)
    # ------------------------------------------------------------------

    async def async_step_import(self, user_input: dict) -> FlowResult:
        if _has_latest_entry(self.hass):
            return self.async_abort(reason="already_configured")
        return self.async_create_entry(
            title="YouTube Latest",
            data={
                CONF_ENTRY_TYPE: ENTRY_TYPE_LATEST,
                CONF_LATEST_COUNT: user_input.get(CONF_LATEST_COUNT, DEFAULT_LATEST_COUNT),
            },
        )

    # ------------------------------------------------------------------
    # Latest feed entry (manual, kept for options flow compatibility)
    # ------------------------------------------------------------------

    async def async_step_latest(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title="YouTube Latest",
                data={
                    CONF_ENTRY_TYPE: ENTRY_TYPE_LATEST,
                    CONF_LATEST_COUNT: user_input[CONF_LATEST_COUNT],
                },
            )

        return self.async_show_form(
            step_id="latest",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_LATEST_COUNT, default=DEFAULT_LATEST_COUNT): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=50)
                    ),
                }
            ),
        )

    # ------------------------------------------------------------------
    # Options
    # ------------------------------------------------------------------

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        entry_type = config_entry.data.get(CONF_ENTRY_TYPE, ENTRY_TYPE_CHANNEL)
        if entry_type == ENTRY_TYPE_LATEST:
            return YouTubeLatestOptionsFlow(config_entry)
        return YouTubeChannelOptionsFlow(config_entry)


class YouTubeChannelOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        current_channels = self._entry.data.get(CONF_CHANNELS, [])
        current_max = self._entry.options.get(CONF_MAX_VIDEOS, self._entry.data.get(CONF_MAX_VIDEOS, DEFAULT_MAX_VIDEOS))
        current_exclude = self._entry.options.get(CONF_EXCLUDE_SHORTS, self._entry.data.get(CONF_EXCLUDE_SHORTS, DEFAULT_EXCLUDE_SHORTS))

        if user_input is not None:
            channels = _parse_channels(user_input[CONF_CHANNELS])
            if not channels:
                errors[CONF_CHANNELS] = "no_channels"
            else:
                self.hass.config_entries.async_update_entry(
                    self._entry,
                    title=_title_from_channels(channels),
                    data={**self._entry.data, CONF_CHANNELS: channels},
                )
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_MAX_VIDEOS: user_input[CONF_MAX_VIDEOS],
                        CONF_EXCLUDE_SHORTS: user_input[CONF_EXCLUDE_SHORTS],
                    },
                )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CHANNELS, default=", ".join(current_channels)): str,
                    vol.Optional(CONF_MAX_VIDEOS, default=current_max): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=50)
                    ),
                    vol.Optional(CONF_EXCLUDE_SHORTS, default=current_exclude): bool,
                }
            ),
            errors=errors,
        )


class YouTubeLatestOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        current_count = self._entry.options.get(CONF_LATEST_COUNT, self._entry.data.get(CONF_LATEST_COUNT, DEFAULT_LATEST_COUNT))

        if user_input is not None:
            return self.async_create_entry(title="", data={CONF_LATEST_COUNT: user_input[CONF_LATEST_COUNT]})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_LATEST_COUNT, default=current_count): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=50)
                    ),
                }
            ),
        )
