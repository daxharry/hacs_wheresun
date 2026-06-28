"""Register static frontend assets and websocket handlers."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN_META, URL_BASE
from .websocket_api import async_register_websocket_handlers

_LOGGER = logging.getLogger(__name__)


async def async_ensure_frontend(hass: HomeAssistant) -> None:
    """Register frontend assets as early as possible (including during config flow)."""
    meta = hass.data.setdefault(DOMAIN_META, {})

    if not meta.get("frontend_registered"):
        frontend_dir = Path(__file__).parent / "frontend"
        try:
            await hass.http.async_register_static_paths(
                [StaticPathConfig(URL_BASE, str(frontend_dir), cache_headers=False)]
            )
        except RuntimeError:
            _LOGGER.debug("WhereSun static path already registered")
        add_extra_js_url(hass, f"{URL_BASE}/wheresun-config-flow.js?v=0.2.0")
        meta["frontend_registered"] = True
        _LOGGER.debug("WhereSun frontend registered at %s", URL_BASE)

    async_register_websocket_handlers(hass)
