"""Geocode addresses using OpenStreetMap Nominatim."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import NOMINATIM_URL, NOMINATIM_USER_AGENT

_LOGGER = logging.getLogger(__name__)


async def geocode_address(
    session: aiohttp.ClientSession, address: str
) -> dict[str, Any] | None:
    """Resolve an address to coordinates and metadata."""
    params = {
        "q": address.strip(),
        "format": "json",
        "limit": 1,
        "addressdetails": 0,
    }
    headers = {"User-Agent": NOMINATIM_USER_AGENT}

    try:
        async with session.get(NOMINATIM_URL, params=params, headers=headers) as response:
            response.raise_for_status()
            results = await response.json()
    except (aiohttp.ClientError, TimeoutError) as err:
        _LOGGER.warning("Geocoding failed for %s: %s", address, err)
        return None

    if not results:
        return None

    result = results[0]
    try:
        latitude = float(result["lat"])
        longitude = float(result["lon"])
    except (KeyError, TypeError, ValueError):
        return None

    display_name = result.get("display_name", address.strip())
    return {
        "address": address.strip(),
        "display_name": display_name,
        "latitude": latitude,
        "longitude": longitude,
    }
