from __future__ import annotations

from typing import Any, Iterable

import h3


def latlng_to_cell(lat: float, lng: float, res: int) -> str:
    return h3.latlng_to_cell(lat, lng, res)


def get_resolution(cell: str) -> int:
    return h3.get_resolution(cell)


def cell_to_parent(cell: str, res: int) -> str:
    return h3.cell_to_parent(cell, res)


def cell_to_children(cell: str, res: int) -> list[str]:
    return list(h3.cell_to_children(cell, res))


def grid_disk(cell: str, k: int) -> list[str]:
    return list(h3.grid_disk(cell, k))


def grid_distance(cell_a: str, cell_b: str) -> int:
    return int(h3.grid_distance(cell_a, cell_b))


def cell_to_latlng(cell: str) -> tuple[float, float]:
    return h3.cell_to_latlng(cell)


def cell_to_boundary(cell: str) -> list[tuple[float, float]]:
    return h3.cell_to_boundary(cell)


def cell_area_km2(cell: str) -> float:
    return float(h3.cell_area(cell, unit="km^2"))


def average_edge_length_km(res: int) -> float:
    return float(h3.average_hexagon_edge_length(res, unit="km"))


def compact_cells(cells: Iterable[str]) -> list[str]:
    return list(h3.compact_cells(list(cells)))


def _latlng_ring_from_geojson(ring: list[list[float]]) -> list[tuple[float, float]]:
    return [(lat, lng) for lng, lat in ring]


def _latlng_poly_from_geojson(geometry: dict[str, Any]) -> h3.LatLngPoly:
    coords = geometry.get("coordinates", [])
    outer = _latlng_ring_from_geojson(coords[0])
    holes = [_latlng_ring_from_geojson(ring) for ring in coords[1:]]
    return h3.LatLngPoly(outer, *holes)


def _latlng_multipoly_from_geojson(geometry: dict[str, Any]) -> h3.LatLngMultiPoly:
    polys = []
    for polygon in geometry.get("coordinates", []):
        outer = _latlng_ring_from_geojson(polygon[0])
        holes = [_latlng_ring_from_geojson(ring) for ring in polygon[1:]]
        polys.append(h3.LatLngPoly(outer, *holes))
    return h3.LatLngMultiPoly(*polys)


def polygon_to_cells(geometry: dict[str, Any], res: int) -> list[str]:
    geom_type = geometry.get("type")
    if geom_type == "Polygon":
        shape = _latlng_poly_from_geojson(geometry)
        return list(h3.polygon_to_cells(shape, res))
    if geom_type == "MultiPolygon":
        shape = _latlng_multipoly_from_geojson(geometry)
        return list(h3.polygon_to_cells(shape, res))
    raise ValueError(f"Unsupported polygon geometry type: {geom_type}")


def line_to_cells(geometry: dict[str, Any], res: int) -> list[str]:
    geom_type = geometry.get("type")
    if geom_type == "LineString":
        line_strings = [geometry.get("coordinates", [])]
    elif geom_type == "MultiLineString":
        line_strings = geometry.get("coordinates", [])
    else:
        raise ValueError(f"Unsupported line geometry type: {geom_type}")

    cells: set[str] = set()
    for line in line_strings:
        if len(line) == 0:
            continue
        line_cells = [latlng_to_cell(lat, lng, res) for lng, lat in line]
        for start, end in zip(line_cells, line_cells[1:]):
            cells.update(h3.grid_path_cells(start, end))
        cells.update(line_cells)
    return sorted(cells)
