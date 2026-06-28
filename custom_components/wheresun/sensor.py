"""Sensor platform for WhereSun."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WhereSunCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WhereSun sensor."""
    coordinator: WhereSunCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WhereSunSensor(coordinator, entry)])


class WhereSunSensor(CoordinatorEntity[WhereSunCoordinator], SensorEntity):
    """Expose sun and moon elevation as a sensor."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_icon = "mdi:home-analytics"
    _attr_native_unit_of_measurement = "°"

    def __init__(self, coordinator: WhereSunCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "WhereSun",
            "model": "House Shadow",
        }

    @property
    def native_value(self) -> float:
        data = self.coordinator.data or {}
        sun_elevation = data.get("sun_elevation", 0.0)
        if sun_elevation > 0:
            return round(float(sun_elevation), 2)
        return round(float(data.get("moon_elevation", 0.0)), 2)

    @property
    def extra_state_attributes(self) -> dict[str, float | str]:
        data = self.coordinator.data or {}
        return {
            "address": self._entry.data.get("address", ""),
            "sun_azimuth": round(float(data.get("sun_azimuth", 0.0)), 2),
            "sun_elevation": round(float(data.get("sun_elevation", 0.0)), 2),
            "moon_azimuth": round(float(data.get("moon_azimuth", 0.0)), 2),
            "moon_elevation": round(float(data.get("moon_elevation", 0.0)), 2),
            "svg_path": self.coordinator.shadow.conf.output_path,
        }
