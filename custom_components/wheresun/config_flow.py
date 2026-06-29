"""Config flow for the WhereSun integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from timezonefinder import TimezoneFinder

from homeassistant import config_entries
from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import get_url

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
    SUBENTRY_HOUSE,
    UNIQUE_ID,
    URL_BASE,
)
from .editor_state import get_editor_blocks, seed_editor_blocks, set_active_flow
from .frontend_setup import async_ensure_frontend
from .geocode import geocode_address
from .geometry import rects_to_polygon

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


def _house_subentry_payload(
    blocks: list[dict[str, Any]], shape: list[dict[str, float]]
) -> dict[str, Any]:
    return {
        "subentry_type": SUBENTRY_HOUSE,
        "title": "House layout",
        "unique_id": "house",
        "data": {
            CONF_BLOCKS: blocks,
            CONF_SHAPE: shape,
        },
    }


def _editor_placeholders(hass: HomeAssistant, flow_id: str) -> dict[str, str]:
    """Placeholders for config flow descriptions (hash avoids HA markdown ? parsing)."""
    base = get_url(hass).rstrip("/")
    return {
        "editor_url": f"{base}{URL_BASE}/editor.html#flow_id={flow_id}",
    }


class HouseSubentryFlowHandler(ConfigSubentryFlow):
    """Handle house layout subentry add and reconfigure flows."""

    async def _async_show_house_editor(
        self,
        user_input: dict[str, Any] | None,
        blocks: list[dict[str, Any]] | None,
    ) -> SubentryFlowResult:
        await async_ensure_frontend(self.hass)
        errors: dict[str, str] = {}

        if user_input is not None:
            saved_blocks = get_editor_blocks(self.hass, self.flow_id)
            if not saved_blocks:
                errors["base"] = "no_blocks"
            else:
                shape = rects_to_polygon(saved_blocks)
                if not shape:
                    errors["base"] = "invalid_shape"
                else:
                    house_data = {
                        CONF_BLOCKS: saved_blocks,
                        CONF_SHAPE: shape,
                    }
                    if self.source == config_entries.SOURCE_RECONFIGURE:
                        return self.async_update_and_abort(
                            self._get_entry(),
                            self._get_reconfigure_subentry(),
                            data=house_data,
                        )
                    return self.async_create_entry(
                        title="House layout",
                        data=house_data,
                    )

        set_active_flow(self.hass, self.flow_id)
        seed_editor_blocks(self.hass, self.flow_id, blocks, force=True)

        return self.async_show_form(
            step_id="reconfigure" if self.source == config_entries.SOURCE_RECONFIGURE else "user",
            data_schema=vol.Schema({}),
            description_placeholders=_editor_placeholders(self.hass, self.flow_id),
            errors=errors,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Add a house layout subentry."""
        return await self._async_show_house_editor(user_input, None)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Reconfigure the house layout subentry."""
        subentry = self._get_reconfigure_subentry()
        return await self._async_show_house_editor(
            user_input, subentry.data.get(CONF_BLOCKS)
        )


class WhereSunConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WhereSun."""

    VERSION = 2

    def __init__(self) -> None:
        self._address_data: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return WhereSunOptionsFlow(config_entry)

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: config_entries.ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return supported subentry types."""
        return {SUBENTRY_HOUSE: HouseSubentryFlowHandler}

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
                        data=self._address_data,
                        options=_default_options(),
                        subentries=[_house_subentry_payload(blocks, shape)],
                    )

        set_active_flow(self.hass, self.flow_id)
        seed_editor_blocks(self.hass, self.flow_id, force=True)

        return self.async_show_form(
            step_id="house",
            data_schema=vol.Schema({}),
            description_placeholders=_editor_placeholders(self.hass, self.flow_id),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Reconfigure the address of the installation."""
        await async_ensure_frontend(self.hass)
        entry = self._get_reconfigure_entry()
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

                data_updates = {
                    **result,
                    CONF_TIMEZONE: timezone,
                    "elevation": entry.data.get(
                        "elevation", self.hass.config.elevation or 0
                    ),
                }
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=data_updates,
                    title=result.get("display_name", entry.title),
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ADDRESS, default=entry.data.get(CONF_ADDRESS, "")
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                    ),
                }
            ),
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
