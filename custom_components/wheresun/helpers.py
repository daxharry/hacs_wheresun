"""Build runtime configuration objects from a config entry."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_BG_COLOR,
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
    DEFAULT_WIDTH,
)
from .shadow_core import Shadow, ShadowConfig, VisualConfig


def build_shadow_config(hass: HomeAssistant, entry: ConfigEntry) -> ShadowConfig:
    """Create location configuration for the shadow engine."""
    options = entry.options
    output_path = hass.config.path(
        options.get(CONF_OUTPUT_PATH, DEFAULT_OUTPUT_PATH)
    )
    return ShadowConfig(
        latitude=entry.data["latitude"],
        longitude=entry.data["longitude"],
        altitude=entry.data.get("elevation", hass.config.elevation or 0),
        timezone=entry.data[CONF_TIMEZONE],
        town=entry.data.get("display_name", entry.data["address"]),
        output_path=output_path,
    )


def build_visual_config(entry: ConfigEntry) -> VisualConfig:
    """Create visual configuration for the shadow engine."""
    options = entry.options
    return VisualConfig(
        width=int(options.get(CONF_WIDTH, DEFAULT_WIDTH)),
        height=int(options.get(CONF_HEIGHT, DEFAULT_HEIGHT)),
        bg_color=options.get(CONF_BG_COLOR, DEFAULT_BG_COLOR),
        primary_color=options.get(CONF_PRIMARY_COLOR, DEFAULT_PRIMARY_COLOR),
        light_color=options.get(CONF_LIGHT_COLOR, DEFAULT_LIGHT_COLOR),
        sun_color=options.get(CONF_SUN_COLOR, DEFAULT_SUN_COLOR),
        moon_color=options.get(CONF_MOON_COLOR, DEFAULT_MOON_COLOR),
        sun_radius=float(options.get(CONF_SUN_RADIUS, DEFAULT_SUN_RADIUS)),
        moon_radius=float(options.get(CONF_MOON_RADIUS, DEFAULT_MOON_RADIUS)),
        shape=list(entry.data.get(CONF_SHAPE, [])),
    )


def build_shadow(hass: HomeAssistant, entry: ConfigEntry) -> Shadow:
    """Create a configured shadow engine instance."""
    return Shadow(build_shadow_config(hass, entry), build_visual_config(entry))
