"""Register static frontend assets and websocket handlers."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import panel_custom
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN_META, URL_BASE
from .websocket_api import async_register_websocket_handlers

_LOGGER = logging.getLogger(__name__)

JS_VERSION = "0.2.4"
PANEL_PATH = "wheresun-house"


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
        await resources.async_create_item({"res_type": "module", "url": url})
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("WhereSun lovelace resource not registered: %s", err)


async def _register_panel(hass: HomeAssistant) -> None:
    """Register a Home Assistant panel for the house layout editor."""
    meta = hass.data.setdefault(DOMAIN_META, {})
    if meta.get("panel_registered"):
        return
    panel_url = f"{URL_BASE}/wheresun-panel.js?v={JS_VERSION}"
    try:
        await panel_custom.async_register_panel(
            hass,
            frontend_url_path=PANEL_PATH,
            webcomponent_name="wheresun-house-panel",
            module_url=panel_url,
            embed_iframe=False,
            require_admin=False,
        )
        meta["panel_registered"] = True
        _LOGGER.debug("WhereSun panel registered at /%s", PANEL_PATH)
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("WhereSun panel registration failed: %s", err)


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
        inject_url = f"{URL_BASE}/wheresun-inject.js?v={JS_VERSION}"
        # Modern HA loads extra_module_url via import(); ES5 bucket is ignored on latest.
        add_extra_js_url(hass, loader_url, es5=False)
        add_extra_js_url(hass, inject_url, es5=False)
        add_extra_js_url(hass, loader_url, es5=True)
        add_extra_js_url(hass, inject_url, es5=True)
        await _register_lovelace_resource(hass, loader_url)
        await _register_panel(hass)
        meta["frontend_registered"] = True
        _LOGGER.debug("WhereSun frontend registered at %s", URL_BASE)

    async_register_websocket_handlers(hass)
