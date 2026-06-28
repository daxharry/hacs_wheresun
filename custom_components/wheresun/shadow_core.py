"""Core sun/moon shadow SVG generation engine."""

from __future__ import annotations

import asyncio
import logging
import math
import os
import zoneinfo
from dataclasses import dataclass
from datetime import datetime

import pylunar
from astral import Observer, moon
from astral import sun as astral_sun
from astral.location import LocationInfo

_LOGGER = logging.getLogger(__name__)

HOURS = 1


@dataclass
class VisualConfig:
    """Visual appearance and house shape."""

    width: int = 100
    height: int = 100
    bg_color: str = "#1a1919"
    primary_color: str = "#1b3024"
    light_color: str = "#26bf75"
    sun_color: str = "#ffff66"
    moon_color: str = "#999999"
    sun_radius: float = 5
    moon_radius: float = 3
    shape: list[dict[str, float]] | None = None

    def __post_init__(self) -> None:
        if self.shape is None:
            self.shape = []


@dataclass
class ShadowConfig:
    """Location and output settings."""

    latitude: float
    longitude: float
    altitude: float
    timezone: str
    town: str
    output_path: str


class Shadow:
    """Generate SVG graphics showing sun/moon position and house shadow."""

    def __init__(self, conf: ShadowConfig, visual: VisualConfig) -> None:
        self.conf = conf
        self.visual = visual
        self.location = LocationInfo(
            conf.town, conf.timezone, conf.latitude, conf.longitude
        )
        self.timezone = zoneinfo.ZoneInfo(conf.timezone)
        self.now = datetime.now(self.timezone)
        self.nowUTC = datetime.now(zoneinfo.ZoneInfo("UTC"))

        self._observer = Observer(
            latitude=self.conf.latitude,
            longitude=self.conf.longitude,
            elevation=self.conf.altitude,
        )

        self._refresh_astronomy()

    def _refresh_astronomy(self, when: datetime | None = None) -> None:
        self.now = when or datetime.now(self.timezone)
        self.nowUTC = self.now.astimezone(zoneinfo.ZoneInfo("UTC"))

        self.sun_data = astral_sun.sun(
            self._observer, date=self.now.date(), tzinfo=self.timezone
        )
        self.sunrise_azimuth = astral_sun.azimuth(self._observer, self.sun_data["sunrise"])
        self.sunset_azimuth = astral_sun.azimuth(self._observer, self.sun_data["sunset"])
        self.sun_azimuth = astral_sun.azimuth(self._observer, self.now)
        self.sun_elevation = astral_sun.elevation(self._observer, self.now)

        self.degs: list[float] = []
        local_date = self.now.date()
        for hour in range(0, 24, HOURS):
            hour_time = datetime(
                local_date.year,
                local_date.month,
                local_date.day,
                hour,
                0,
                0,
                tzinfo=self.timezone,
            )
            azimuth = astral_sun.azimuth(self._observer, hour_time)
            self.degs.append(float(azimuth) if azimuth is not None else 0.0)

        if self.conf.latitude < 0:
            self.sunrise_azimuth = (self.sunrise_azimuth + 180) % 360
            self.sunset_azimuth = (self.sunset_azimuth + 180) % 360
            self.sun_azimuth = (self.sun_azimuth + 180) % 360
            self.degs = [(deg + 180) % 360 for deg in self.degs]

        self.moon_info = pylunar.MoonInfo(
            self.decdeg2dms(self.conf.latitude),
            self.decdeg2dms(self.conf.longitude),
        )
        self.moon_info.update(self.nowUTC.replace(tzinfo=None))
        self.moon_azimuth = self.moon_info.azimuth()
        self.moon_elevation = self.moon_info.altitude()
        self.elevation = (
            self.sun_elevation if self.sun_elevation > 0 else self.moon_elevation
        )

    def refresh(self, override_time: datetime | None = None) -> None:
        """Recalculate astronomical data."""
        self._refresh_astronomy(override_time)

    @staticmethod
    def decdeg2dms(dd: float) -> tuple[int, int, int]:
        negative = dd < 0
        dd = abs(dd)
        minutes, seconds = divmod(dd * 3600, 60)
        degrees, minutes = divmod(minutes, 60)
        if negative:
            if degrees > 0:
                degrees = -degrees
            elif minutes > 0:
                minutes = -minutes
            else:
                seconds = -seconds
        return int(degrees), int(minutes), int(seconds)

    def azimuth_to_point(
        self,
        azimuth_deg: float,
        radius: float,
        cx: float | None = None,
        cy: float | None = None,
    ) -> dict[str, float]:
        cx = self.visual.width / 2 if cx is None else cx
        cy = self.visual.height / 2 if cy is None else cy
        theta = math.radians(azimuth_deg)
        return {
            "x": cx + radius * math.sin(theta),
            "y": cy - radius * math.cos(theta),
        }

    @staticmethod
    def generate_path(
        stroke: str,
        fill: str,
        points: list[dict[str, float]],
        attrs: str | None = None,
    ) -> str:
        path_data = "M " + " ".join(f"{pt['x']:.2f},{pt['y']:.2f}" for pt in points) + " Z"
        extra = f" {attrs}" if attrs else ""
        return (
            f'<path stroke="{stroke}" fill="{fill}" d="{path_data}"{extra} />'
        )

    def generate_arc(
        self,
        dist: float,
        stroke: str,
        fill: str | None,
        start: float,
        end: float,
        attrs: str | None = None,
    ) -> str:
        angle = end - start
        if angle < 0:
            angle = 360 + angle
        start_pt = self.azimuth_to_point(start, dist)
        end_pt = self.azimuth_to_point(end, dist)
        large_arc = 1 if angle > 180 else 0
        extra = attrs or ""
        return (
            f'<path d="M {start_pt["x"]:.2f},{start_pt["y"]:.2f} '
            f'A {dist},{dist} 0 {large_arc},1 {end_pt["x"]:.2f},{end_pt["y"]:.2f}" '
            f'stroke="{stroke}" fill="{fill or "none"}" {extra}/>'
        )

    @staticmethod
    def _calculate_min_max(
        shape: list[dict[str, float]], real_pos: dict[str, float]
    ) -> tuple[int, int]:
        min_point = -1
        max_point = -1
        min_angle = 999.0
        max_angle = -999.0
        for index, point in enumerate(shape):
            angle = -math.degrees(
                math.atan2(point["y"] - real_pos["y"], point["x"] - real_pos["x"])
            )
            if angle < min_angle:
                min_angle = angle
                min_point = index
            if angle > max_angle:
                max_angle = angle
                max_point = index
        return min_point, max_point

    @staticmethod
    def _slice_shape(
        shape: list[dict[str, float]], start: int, end: int
    ) -> list[dict[str, float]]:
        output: list[dict[str, float]] = []
        index = start
        while True:
            output.append(shape[index])
            if index == end:
                break
            index = (index + 1) % len(shape)
        return output

    @staticmethod
    def _project_point(
        point: dict[str, float], shadow_length: float, azimuth_deg: float
    ) -> dict[str, float]:
        opp_deg = -azimuth_deg + 270.0
        vx = math.cos(math.radians(opp_deg))
        vy = math.sin(math.radians(opp_deg))
        return {
            "x": point["x"] + shadow_length * vx,
            "y": point["y"] - shadow_length * vy,
        }

    def _svg_header(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {self.visual.width} {self.visual.height}">'
            f'<rect width="{self.visual.width}" height="{self.visual.height}" '
            f'fill="{self.visual.bg_color}" />'
        )

    def _svg_shadow_mask(self) -> str:
        return (
            "<defs>"
            '<mask id="shadowMask">'
            f'<rect width="{self.visual.width}" height="{self.visual.height}" fill="white" />'
            f'{self.generate_path("none", "black", self.visual.shape or [])}'
            "</mask>"
            "</defs>"
        )

    def _svg_outline(self) -> str:
        return self.generate_path(
            "none", self.visual.primary_color, self.visual.shape or []
        )

    def _svg_shadow(
        self,
        shape: list[dict[str, float]],
        sun_pos: dict[str, float],
        moon_pos: dict[str, float],
    ) -> str:
        use_sun = self.sun_elevation > 0
        use_moon = (not use_sun) and (self.moon_elevation > 0)
        if not (use_sun or use_moon):
            return self.generate_path(self.visual.primary_color, "none", shape)

        elevation = self.sun_elevation if use_sun else self.moon_elevation
        azimuth_deg = self.sun_azimuth if use_sun else self.moon_azimuth
        base_pos = sun_pos if use_sun else moon_pos

        cx = self.visual.width / 2.0
        cy = self.visual.height / 2.0
        ux = base_pos["x"] - cx
        uy = base_pos["y"] - cy
        norm = math.hypot(ux, uy) or 1.0
        real_pos = {
            "x": cx + (ux / norm) * 10000.0,
            "y": cy + (uy / norm) * 10000.0,
        }

        min_idx, max_idx = self._calculate_min_max(shape, real_pos)
        if min_idx < 0 or max_idx < 0:
            return self.generate_path(self.visual.primary_color, "none", shape)
        if min_idx == max_idx and len(shape) > 1:
            distances = [
                (math.hypot(point["x"] - real_pos["x"], point["y"] - real_pos["y"]), i)
                for i, point in enumerate(shape)
            ]
            max_idx = max(
                (item for item in distances if item[1] != min_idx),
                key=lambda item: item[0],
            )[1]

        bright_side = self._slice_shape(shape, min_idx, max_idx)
        dark_side = self._slice_shape(shape, max_idx, min_idx)
        if not bright_side or not dark_side:
            return self.generate_path(self.visual.primary_color, "none", shape)

        shadow_length = min(
            self.visual.width * 2,
            self.visual.width / max(0.001, math.tan(math.radians(elevation))),
        )
        min_proj = self._project_point(shape[min_idx], shadow_length, azimuth_deg)
        max_proj = self._project_point(shape[max_idx], shadow_length, azimuth_deg)

        shadow = [max_proj] + dark_side + [min_proj]
        shadow_svg = self.generate_path(
            "none",
            "black",
            shadow,
            'mask="url(#shadowMask)" fill-opacity="0.5"',
        )
        shape_svg = self.generate_path(self.visual.primary_color, "none", shape)
        light_svg = self.generate_path(self.visual.light_color, "none", bright_side)
        return shape_svg + light_svg + shadow_svg

    def _svg_day_night_arcs(self) -> str:
        radius = self.visual.width / 2
        return (
            self.generate_arc(
                radius, self.visual.primary_color, "none", self.sunset_azimuth, self.sunrise_azimuth
            )
            + self.generate_arc(
                radius, self.visual.light_color, "none", self.sunrise_azimuth, self.sunset_azimuth
            )
        )

    def _svg_sunrise_sunset_ticks(self) -> str:
        radius = self.visual.width / 2
        return (
            self.generate_path(
                self.visual.light_color,
                "none",
                [
                    self.azimuth_to_point(self.sunrise_azimuth, radius - 2),
                    self.azimuth_to_point(self.sunrise_azimuth, radius + 2),
                ],
            )
            + self.generate_path(
                self.visual.light_color,
                "none",
                [
                    self.azimuth_to_point(self.sunset_azimuth, radius - 2),
                    self.azimuth_to_point(self.sunset_azimuth, radius + 2),
                ],
            )
        )

    def _svg_hour_arcs(self) -> str:
        svg = ""
        radius = self.visual.width / 2 + 8
        for index in range(len(self.degs)):
            next_index = 0 if index == len(self.degs) - 1 else index + 1
            attrs = 'stroke-width="3" stroke-opacity="0.2"' if index % 2 == 0 else 'stroke-width="3"'
            svg += self.generate_arc(
                radius,
                self.visual.primary_color,
                "none",
                self.degs[index],
                self.degs[next_index],
                attrs,
            )
        return svg

    def _svg_ticks_midnight_noon(self) -> str:
        radius_outer = self.visual.width / 2 + 11
        radius_inner = self.visual.width / 2 + 5
        noon_index = len(self.degs) // 2
        return (
            self.generate_path(
                self.visual.light_color,
                "none",
                [
                    self.azimuth_to_point(self.degs[0], radius_inner),
                    self.azimuth_to_point(self.degs[0], radius_outer),
                ],
            )
            + self.generate_path(
                self.visual.light_color,
                "none",
                [
                    self.azimuth_to_point(self.degs[noon_index], radius_inner),
                    self.azimuth_to_point(self.degs[noon_index], radius_outer),
                ],
            )
        )

    def _svg_sun_marker(self, sun_pos: dict[str, float]) -> str:
        if self.sun_elevation <= 0:
            return ""
        return (
            f'<circle cx="{sun_pos["x"]:.2f}" cy="{sun_pos["y"]:.2f}" '
            f'r="{self.visual.sun_radius}" fill="{self.visual.sun_color}" />'
            f'<circle cx="{sun_pos["x"]:.2f}" cy="{sun_pos["y"]:.2f}" '
            f'r="{self.visual.sun_radius + 1}" fill="none" stroke="{self.visual.sun_color}" '
            f'stroke-width="0.5" />'
        )

    def _svg_moon_marker(self, moon_pos: dict[str, float]) -> str:
        if self.moon_elevation <= 0:
            return ""

        phase = moon.phase(self.now)
        left_radius = self.visual.moon_radius
        left_sweep = 0
        right_radius = self.visual.moon_radius
        right_sweep = 0

        if phase > 14:
            right_radius = self.visual.moon_radius - (
                2.0
                * self.visual.moon_radius
                * (1.0 - ((phase % 14) * 0.99 / 14.0))
            )
            if right_radius < 0:
                right_radius = -right_radius
            right_sweep = 0
        else:
            right_sweep = 1

        if phase < 14:
            left_radius = self.visual.moon_radius - (
                2.0
                * self.visual.moon_radius
                * (1.0 - ((phase % 14) * 0.99 / 14.0))
            )
            if left_radius < 0:
                left_radius = -left_radius
            left_sweep = 1

        x = moon_pos["x"]
        y = moon_pos["y"]
        r = self.visual.moon_radius
        return (
            f'<path d="M {x - r:.2f},{y:.2f} '
            f'A {left_radius},{r} 0 0,{left_sweep} {x + r:.2f},{y:.2f} '
            f'A {right_radius},{r} 0 0,{right_sweep} {x - r:.2f},{y:.2f} Z" '
            f'fill="{self.visual.moon_color}" />'
        )

    def _svg_timestamp(self) -> str:
        timestamp = self.now.strftime("%Y-%m-%d %H:%M:%S")
        return (
            f'<text x="2" y="{self.visual.height - 2}" '
            f'font-size="3" fill="{self.visual.light_color}">{timestamp}</text>'
        )

    def _build_svg(self) -> str:
        radius = self.visual.width / 2
        sun_pos = self.azimuth_to_point(self.sun_azimuth, radius)
        moon_pos = self.azimuth_to_point(self.moon_azimuth, radius)
        shape = self.visual.shape or []

        svg = self._svg_header()
        svg += self._svg_shadow_mask()
        svg += self._svg_outline()
        svg += self._svg_shadow(shape, sun_pos, moon_pos)
        svg += self._svg_day_night_arcs()
        svg += self._svg_sunrise_sunset_ticks()
        svg += self._svg_hour_arcs()
        svg += self._svg_ticks_midnight_noon()
        svg += self._svg_sun_marker(sun_pos)
        svg += self._svg_moon_marker(moon_pos)
        svg += self._svg_timestamp()
        svg += "</svg>"
        return svg

    def _write_svg(self, svg_content: str) -> None:
        folder = os.path.dirname(self.conf.output_path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        with open(self.conf.output_path, "w", encoding="utf-8") as handle:
            handle.write(svg_content)

    async def async_generate_svg(self, hass) -> str:
        """Refresh astronomy data and write the SVG file."""
        self.refresh()
        svg_content = self._build_svg()
        await hass.async_add_executor_job(self._write_svg, svg_content)
        return svg_content

    def generate_svg(self, hass) -> None:
        """Synchronous wrapper used by manifest actions."""
        asyncio.run_coroutine_threadsafe(
            self.async_generate_svg(hass),
            hass.loop,
        )
