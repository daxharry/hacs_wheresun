"""Data update coordinator for WhereSun."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, DOMAIN
from .helpers import build_shadow

_LOGGER = logging.getLogger(__name__)


class WhereSunCoordinator(DataUpdateCoordinator[dict[str, float]]):
    """Periodically refresh astronomy data and regenerate the SVG."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        interval_minutes = int(
            entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        )
        self.entry = entry
        self.shadow = build_shadow(hass, entry)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=interval_minutes),
        )

    async def _async_update_data(self) -> dict[str, float]:
        try:
            await self.shadow.async_generate_svg(self.hass)
        except OSError as err:
            raise UpdateFailed(f"Unable to write SVG file: {err}") from err

        return {
            "sun_azimuth": float(self.shadow.sun_azimuth),
            "sun_elevation": float(self.shadow.sun_elevation),
            "moon_azimuth": float(self.shadow.moon_azimuth),
            "moon_elevation": float(self.shadow.moon_elevation),
        }

    def rebuild_shadow(self, hass: HomeAssistant) -> None:
        """Rebuild the shadow engine after configuration changes."""
        self.shadow = build_shadow(hass, self.entry)
