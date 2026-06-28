"""Camera platform for WhereSun."""

from __future__ import annotations

import logging
import mimetypes

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import WhereSunCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WhereSun camera."""
    coordinator: WhereSunCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WhereSunCamera(coordinator, entry)])


class WhereSunCamera(Camera):
    """Expose the generated SVG through a camera entity."""

    _attr_has_entity_name = True
    _attr_name = "Shadow"

    def __init__(self, coordinator: WhereSunCoordinator, entry: ConfigEntry) -> None:
        super().__init__()
        self._coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_camera"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "WhereSun",
            "model": "House Shadow",
        }

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return the latest SVG bytes."""
        path = self._coordinator.shadow.conf.output_path
        try:
            return await self.hass.async_add_executor_job(_read_file, path)
        except OSError as err:
            _LOGGER.warning("Unable to read SVG at %s: %s", path, err)
            return None

    @property
    def content_type(self) -> str:
        """Return the mime type for the SVG image."""
        path = self._coordinator.shadow.conf.output_path
        mime, _ = mimetypes.guess_type(path)
        return mime or "image/svg+xml"


def _read_file(path: str) -> bytes:
    with open(path, "rb") as handle:
        return handle.read()
