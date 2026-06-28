"""Convert axis-aligned rectangles into a single outer polygon."""

from __future__ import annotations

from typing import Any


def _point_in_rect(x: float, y: float, block: dict[str, Any]) -> bool:
    return (
        float(block["x"]) <= x <= float(block["x"]) + float(block["width"])
        and float(block["y"]) <= y <= float(block["y"]) + float(block["height"])
    )


def _largest_rect_polygon(blocks: list[dict[str, Any]]) -> list[dict[str, float]]:
    largest = max(blocks, key=lambda b: float(b["width"]) * float(b["height"]))
    x = float(largest["x"])
    y = float(largest["y"])
    w = float(largest["width"])
    h = float(largest["height"])
    return [
        {"x": x, "y": y},
        {"x": x + w, "y": y},
        {"x": x + w, "y": y + h},
        {"x": x, "y": y + h},
    ]


def _macro_cells(blocks: list[dict[str, Any]]) -> tuple[list[float], list[float], list[list[bool]]]:
    xs = sorted(
        {
            round(float(block["x"]), 4)
            for block in blocks
        }
        | {
            round(float(block["x"]) + float(block["width"]), 4)
            for block in blocks
        }
    )
    ys = sorted(
        {
            round(float(block["y"]), 4)
            for block in blocks
        }
        | {
            round(float(block["y"]) + float(block["height"]), 4)
            for block in blocks
        }
    )

    grid: list[list[bool]] = []
    for y_index in range(len(ys) - 1):
        row: list[bool] = []
        mid_y = (ys[y_index] + ys[y_index + 1]) / 2
        for x_index in range(len(xs) - 1):
            mid_x = (xs[x_index] + xs[x_index + 1]) / 2
            row.append(any(_point_in_rect(mid_x, mid_y, block) for block in blocks))
        grid.append(row)
    return xs, ys, grid


def _boundary_edges(
    xs: list[float], ys: list[float], grid: list[list[bool]]
) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    edges: list[tuple[tuple[float, float], tuple[float, float]]] = []
    height = len(grid)
    width = len(grid[0]) if height else 0

    for y_index in range(height):
        for x_index in range(width):
            if not grid[y_index][x_index]:
                continue
            x1, x2 = xs[x_index], xs[x_index + 1]
            y1, y2 = ys[y_index], ys[y_index + 1]
            if y_index == 0 or not grid[y_index - 1][x_index]:
                edges.append(((x1, y1), (x2, y1)))
            if x_index == width - 1 or not grid[y_index][x_index + 1]:
                edges.append(((x2, y1), (x2, y2)))
            if y_index == height - 1 or not grid[y_index + 1][x_index]:
                edges.append(((x2, y2), (x1, y2)))
            if x_index == 0 or not grid[y_index][x_index - 1]:
                edges.append(((x1, y2), (x1, y1)))
    return edges


def _edges_to_polygon(
    edges: list[tuple[tuple[float, float], tuple[float, float]]],
) -> list[dict[str, float]]:
    if not edges:
        return []

    adjacency: dict[tuple[float, float], list[tuple[float, float]]] = {}
    for start, end in edges:
        adjacency.setdefault(start, []).append(end)

    start = edges[0][0]
    polygon: list[tuple[float, float]] = [start]
    previous = None
    current = start

    for _ in range(len(edges) + 2):
        neighbors = adjacency.get(current, [])
        if not neighbors:
            break
        nxt = neighbors[0] if neighbors[0] != previous else neighbors[-1]
        if nxt == start and len(polygon) > 2:
            break
        polygon.append(nxt)
        previous, current = current, nxt

    if len(polygon) < 3:
        return []

    simplified: list[dict[str, float]] = []
    for index, point in enumerate(polygon):
        prev_point = polygon[index - 1]
        next_point = polygon[(index + 1) % len(polygon)]
        same_x = abs(prev_point[0] - point[0]) < 0.001 and abs(point[0] - next_point[0]) < 0.001
        same_y = abs(prev_point[1] - point[1]) < 0.001 and abs(point[1] - next_point[1]) < 0.001
        if same_x or same_y:
            continue
        simplified.append({"x": round(point[0], 2), "y": round(point[1], 2)})

    return simplified or [
        {"x": round(point[0], 2), "y": round(point[1], 2)} for point in polygon
    ]


def rects_to_polygon(blocks: list[dict[str, Any]]) -> list[dict[str, float]]:
    """Merge rectangles into one outer polygon suitable for shadow rendering."""
    if not blocks:
        return []
    if len(blocks) == 1:
        return _largest_rect_polygon(blocks)

    xs, ys, grid = _macro_cells(blocks)
    if len(xs) < 2 or len(ys) < 2:
        return _largest_rect_polygon(blocks)

    polygon = _edges_to_polygon(_boundary_edges(xs, ys, grid))
    return polygon if len(polygon) >= 3 else _largest_rect_polygon(blocks)
