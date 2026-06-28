"""Tests for rectangle to polygon conversion."""

import importlib.util
from pathlib import Path


def _load_geometry():
    path = Path(__file__).resolve().parents[1] / "custom_components/wheresun/geometry.py"
    spec = importlib.util.spec_from_file_location("geometry", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_single_rectangle():
    geometry = _load_geometry()
    blocks = [{"x": 10, "y": 20, "width": 30, "height": 15}]
    shape = geometry.rects_to_polygon(blocks)
    assert shape == [
        {"x": 10.0, "y": 20.0},
        {"x": 40.0, "y": 20.0},
        {"x": 40.0, "y": 35.0},
        {"x": 10.0, "y": 35.0},
    ]


def test_l_shape():
    geometry = _load_geometry()
    blocks = [
        {"x": 10, "y": 10, "width": 30, "height": 10},
        {"x": 10, "y": 20, "width": 10, "height": 20},
    ]
    shape = geometry.rects_to_polygon(blocks)
    assert len(shape) == 6
    assert shape[0] == {"x": 10.0, "y": 10.0}
    assert shape[2] == {"x": 40.0, "y": 20.0}
    assert shape[4] == {"x": 20.0, "y": 40.0}
