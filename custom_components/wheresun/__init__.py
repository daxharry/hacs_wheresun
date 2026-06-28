"""WhereSun Home Assistant integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from .const import CONF_BLOCKS, CONF_SHAPE, DOMAIN, PLATFORMS, SUBENTRY_HOUSE
from .coordinator import WhereSunCoordinator
from .frontend_setup import async_ensure_frontend
from .websocket_api import async_register_websocket_handlers

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the WhereSun domain."""
    await async_ensure_frontend(hass)
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate legacy entries that stored house data on the main config entry."""
    if entry.version > 2:
        return False

    if entry.version != 1:
        return True

    blocks = entry.data.get(CONF_BLOCKS)
    shape = entry.data.get(CONF_SHAPE)
    new_data = {
        key: value
        for key, value in entry.data.items()
        if key not in (CONF_BLOCKS, CONF_SHAPE)
    }

    if blocks and not any(
        subentry.subentry_type == SUBENTRY_HOUSE
        for subentry in entry.subentries.values()
    ):
        try:
            hass.config_entries.async_add_subentry(
                entry,
                ConfigSubentry(
                    data={CONF_BLOCKS: blocks, CONF_SHAPE: shape or []},
                    subentry_type=SUBENTRY_HOUSE,
                    title="House layout",
                    unique_id="house",
                ),
            )
        except AttributeError:
            _LOGGER.warning(
                "Unable to migrate house data to subentry on this Home Assistant version"
            )
            new_data = dict(entry.data)
            hass.config_entries.async_update_entry(entry, data=new_data, version=2)
            return True

    hass.config_entries.async_update_entry(entry, data=new_data, version=2)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up WhereSun from a config entry."""
    await async_ensure_frontend(hass)

    coordinator = WhereSunCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    async_register_websocket_handlers(hass)

    async def handle_generate_svg(call: ServiceCall) -> None:
        await coordinator.shadow.async_generate_svg(hass)
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        "generate_svg",
        handle_generate_svg,
        schema=vol.Schema({}),
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
            hass.services.async_remove(DOMAIN, "generate_svg")
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
