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

JS_VERSION = "0.2.1"


async def _register_lovelace_resource(hass: HomeAssistant, url: str) -> None:
    """Best-effort registration of the editor script as a Lovelace resource."""
    lovelace = hass.data.get("lovelace")
    if not lovelace or getattr(lovelace, "mode", None) != "storage":
        return
    resources = getattr(lovelace, "resources", None)
    if resources is None:
        return
    try:
        existing = await resources.async_get_info()
    except Exception:  # noqa: BLE001
        return
    if any(item.get("url", "").startswith(url.rsplit("?", 1)[0]) for item in existing):
        return
    try:
        await resources.async_create_item({"res_type": "js", "url": url})
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("WhereSun lovelace resource not registered: %s", err)


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

        loader_url = f"{URL_BASE}/wheresun-loader.js?v={JS_VERSION}"
        main_url = f"{URL_BASE}/wheresun-config-flow.js?v={JS_VERSION}"
        add_extra_js_url(hass, loader_url)
        add_extra_js_url(hass, main_url)
        await _register_lovelace_resource(hass, main_url)
        meta["frontend_registered"] = True
        _LOGGER.debug("WhereSun frontend registered at %s", URL_BASE)

    async_register_websocket_handlers(hass)
