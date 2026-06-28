"""WebSocket API helpers for the house editor."""

from __future__ import annotations

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
import voluptuous as vol

from .const import DOMAIN


@callback
def async_register_websocket_handlers(hass: HomeAssistant) -> None:
    """Register websocket commands used by the frontend editor."""
    if hass.data.get(DOMAIN, {}).get("ws_registered"):
        return

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("editor_state", {})
    hass.data[DOMAIN]["ws_registered"] = True

    websocket_api.async_register_command(hass, ws_editor_set)
    websocket_api.async_register_command(hass, ws_editor_get)


@websocket_api.websocket_command(
    {
        "type": f"{DOMAIN}/editor_set",
        vol.Required("flow_id"): str,
        vol.Required("blocks"): list,
    }
)
@websocket_api.async_response
async def ws_editor_set(hass: HomeAssistant, connection, msg: dict) -> None:
    """Store temporary editor blocks for a config flow."""
    hass.data[DOMAIN]["editor_state"][msg["flow_id"]] = msg["blocks"]
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        "type": f"{DOMAIN}/editor_get",
        vol.Required("flow_id"): str,
    }
)
@websocket_api.async_response
async def ws_editor_get(hass: HomeAssistant, connection, msg: dict) -> None:
    """Return temporary editor blocks for a config flow."""
    blocks = hass.data[DOMAIN]["editor_state"].get(msg["flow_id"], [])
    connection.send_result(msg["id"], {"blocks": blocks})
