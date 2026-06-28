"""Store and retrieve temporary editor state during config flow."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .const import DOMAIN, DOMAIN_META

DEFAULT_BLOCKS: list[dict[str, Any]] = [
    {"id": "r1", "x": 35, "y": 40, "width": 30, "height": 25},
]


def _meta(hass: HomeAssistant) -> dict[str, Any]:
    return hass.data.setdefault(DOMAIN_META, {})


def _editor_state(hass: HomeAssistant) -> dict[str, list[dict[str, Any]]]:
    return _meta(hass).setdefault("editor_state", {})


def set_active_flow(hass: HomeAssistant, flow_id: str) -> None:
    """Remember which config flow step is currently showing the editor."""
    _meta(hass)["active_flow_id"] = flow_id


def seed_editor_blocks(
    hass: HomeAssistant,
    flow_id: str,
    blocks: list[dict[str, Any]] | None = None,
    *,
    force: bool = False,
) -> None:
    """Initialize editor blocks for a config flow."""
    state = _editor_state(hass)
    if force or flow_id not in state:
        state[flow_id] = list(blocks or DEFAULT_BLOCKS)


def get_editor_blocks(hass: HomeAssistant, flow_id: str) -> list[dict[str, Any]]:
    """Return blocks saved by the visual editor for a config flow."""
    return list(_editor_state(hass).get(flow_id, []))
