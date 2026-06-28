"""Config flow for the WhereSun integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from timezonefinder import TimezoneFinder

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ADDRESS,
    CONF_BG_COLOR,
    CONF_BLOCKS,
    CONF_HEIGHT,
    CONF_LIGHT_COLOR,
    CONF_MOON_COLOR,
    CONF_MOON_RADIUS,
    CONF_OUTPUT_PATH,
    CONF_PRIMARY_COLOR,
    CONF_SHAPE,
    CONF_SUN_COLOR,
    CONF_SUN_RADIUS,
    CONF_TIMEZONE,
    CONF_UPDATE_INTERVAL,
    CONF_WIDTH,
    DEFAULT_BG_COLOR,
    DEFAULT_HEIGHT,
    DEFAULT_LIGHT_COLOR,
    DEFAULT_MOON_COLOR,
    DEFAULT_MOON_RADIUS,
    DEFAULT_OUTPUT_PATH,
    DEFAULT_PRIMARY_COLOR,
    DEFAULT_SUN_COLOR,
    DEFAULT_SUN_RADIUS,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_WIDTH,
    DOMAIN,
    UNIQUE_ID,
)
from .geocode import geocode_address
from .geometry import rects_to_polygon
from .editor_state import get_editor_blocks, seed_editor_blocks, set_active_flow
from .frontend_setup import async_ensure_frontend

_LOGGER = logging.getLogger(__name__)


def _default_options() -> dict[str, Any]:
    return {
        CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
        CONF_OUTPUT_PATH: DEFAULT_OUTPUT_PATH,
        CONF_WIDTH: DEFAULT_WIDTH,
        CONF_HEIGHT: DEFAULT_HEIGHT,
        CONF_BG_COLOR: DEFAULT_BG_COLOR,
        CONF_PRIMARY_COLOR: DEFAULT_PRIMARY_COLOR,
        CONF_LIGHT_COLOR: DEFAULT_LIGHT_COLOR,
        CONF_SUN_COLOR: DEFAULT_SUN_COLOR,
        CONF_MOON_COLOR: DEFAULT_MOON_COLOR,
        CONF_SUN_RADIUS: DEFAULT_SUN_RADIUS,
        CONF_MOON_RADIUS: DEFAULT_MOON_RADIUS,
    }


class WhereSunConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WhereSun."""

    VERSION = 1

    def __init__(self) -> None:
        self._address_data: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return WhereSunOptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Ask for the mandatory address."""
        await async_ensure_frontend(self.hass)
        await self.async_set_unique_id(UNIQUE_ID)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            result = await geocode_address(session, user_input[CONF_ADDRESS])
            if result is None:
                errors["base"] = "invalid_address"
            else:
                timezone = await self.hass.async_add_executor_job(
                    _lookup_timezone, result["latitude"], result["longitude"]
                )
                if timezone is None:
                    timezone = str(self.hass.config.time_zone)

                self._address_data = {
                    **result,
                    CONF_TIMEZONE: timezone,
                    "elevation": self.hass.config.elevation or 0,
                }
                return await self.async_step_house()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_house(self, user_input: dict[str, Any] | None = None):
        """Collect the house layout from the visual editor."""
        await async_ensure_frontend(self.hass)
        errors: dict[str, str] = {}
        if user_input is not None:
            blocks = get_editor_blocks(self.hass, self.flow_id)
            if not blocks:
                errors["base"] = "no_blocks"
            else:
                shape = rects_to_polygon(blocks)
                if not shape:
                    errors["base"] = "invalid_shape"
                else:
                    return self.async_create_entry(
                        title=self._address_data.get("display_name", "WhereSun"),
                        data={
                            **self._address_data,
                            CONF_BLOCKS: blocks,
                            CONF_SHAPE: shape,
                        },
                        options=_default_options(),
                    )

        set_active_flow(self.hass, self.flow_id)
        seed_editor_blocks(self.hass, self.flow_id)

        return self.async_show_form(
            step_id="house",
            data_schema=vol.Schema({}),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Allow reopening the house editor from the integration page."""
        return await self.async_step_house_reconfigure(user_input)

    async def async_step_house_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ):
        """Update the stored house layout."""
        await async_ensure_frontend(self.hass)
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            blocks = get_editor_blocks(self.hass, self.flow_id)
            if not blocks:
                errors["base"] = "no_blocks"
            else:
                shape = rects_to_polygon(blocks)
                if not shape:
                    errors["base"] = "invalid_shape"
                else:
                    new_data = {
                        **dict(entry.data),
                        CONF_BLOCKS: blocks,
                        CONF_SHAPE: shape,
                    }
                    self.hass.config_entries.async_update_entry(entry, data=new_data)
                    await self.hass.config_entries.async_reload(entry.entry_id)
                    return self.async_abort(reason="reconfigure_successful")

        set_active_flow(self.hass, self.flow_id)
        seed_editor_blocks(self.hass, self.flow_id, entry.data.get(CONF_BLOCKS))

        return self.async_show_form(
            step_id="house_reconfigure",
            data_schema=vol.Schema({}),
            errors=errors,
        )


class WhereSunOptionsFlow(config_entries.OptionsFlow):
    """Handle WhereSun options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage visual and runtime options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_UPDATE_INTERVAL,
                        default=options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1,
                            max=1440,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(
                        CONF_OUTPUT_PATH,
                        default=options.get(CONF_OUTPUT_PATH, DEFAULT_OUTPUT_PATH),
                    ): str,
                    vol.Required(
                        CONF_PRIMARY_COLOR,
                        default=options.get(CONF_PRIMARY_COLOR, DEFAULT_PRIMARY_COLOR),
                    ): selector.ColorSelector(selector.ColorSelectorConfig()),
                    vol.Required(
                        CONF_LIGHT_COLOR,
                        default=options.get(CONF_LIGHT_COLOR, DEFAULT_LIGHT_COLOR),
                    ): selector.ColorSelector(selector.ColorSelectorConfig()),
                    vol.Required(
                        CONF_BG_COLOR,
                        default=options.get(CONF_BG_COLOR, DEFAULT_BG_COLOR),
                    ): selector.ColorSelector(selector.ColorSelectorConfig()),
                    vol.Required(
                        CONF_SUN_COLOR,
                        default=options.get(CONF_SUN_COLOR, DEFAULT_SUN_COLOR),
                    ): selector.ColorSelector(selector.ColorSelectorConfig()),
                    vol.Required(
                        CONF_MOON_COLOR,
                        default=options.get(CONF_MOON_COLOR, DEFAULT_MOON_COLOR),
                    ): selector.ColorSelector(selector.ColorSelectorConfig()),
                    vol.Required(
                        CONF_SUN_RADIUS,
                        default=options.get(CONF_SUN_RADIUS, DEFAULT_SUN_RADIUS),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(min=1, max=20, step=0.5)
                    ),
                    vol.Required(
                        CONF_MOON_RADIUS,
                        default=options.get(CONF_MOON_RADIUS, DEFAULT_MOON_RADIUS),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(min=1, max=20, step=0.5)
                    ),
                }
            ),
        )


def _lookup_timezone(latitude: float, longitude: float) -> str | None:
    finder = TimezoneFinder()
    return finder.timezone_at(lat=latitude, lng=longitude)
