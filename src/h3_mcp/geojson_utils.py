from __future__ import annotations

from typing import Any, Iterable, Iterator, cast


def iter_features(geojson: dict[str, Any]) -> Iterator[dict[str, Any]]:
    if geojson.get("type") == "FeatureCollection":
        for feature in geojson.get("features", []):
            if feature.get("type") != "Feature":
                raise ValueError("FeatureCollection contains a non-Feature item.")
            yield feature
    elif geojson.get("type") == "Feature":
        yield geojson
    else:
        raise ValueError("GeoJSON must be a FeatureCollection or Feature.")


def _iter_coords(geometry: dict[str, Any]) -> Iterable[tuple[float, float]]:
    geom_type = geometry.get("type")
    coords = geometry.get("coordinates")
    if coords is None:
        raise ValueError("Geometry missing coordinates.")
    if geom_type == "Point":
        point = cast(list[float], coords)
        lng, lat = point
        yield lng, lat
    elif geom_type in {"MultiPoint", "LineString"}:
        line = cast(list[list[float]], coords)
        for lng, lat in line:
            yield lng, lat
    elif geom_type in {"MultiLineString", "Polygon"}:
        lines = cast(list[list[list[float]]], coords)
        for ring in lines:
            for lng, lat in ring:
                yield lng, lat
    elif geom_type == "MultiPolygon":
        polygons = cast(list[list[list[list[float]]]], coords)
        for polygon in polygons:
            for ring in polygon:
                for lng, lat in ring:
                    yield lng, lat
    else:
        raise ValueError(f"Unsupported geometry type: {geom_type}")


def bounding_box_from_geojson(geojson: dict[str, Any]) -> list[float]:
    min_lng = min_lat = float("inf")
    max_lng = max_lat = float("-inf")
    for feature in iter_features(geojson):
        geometry = feature.get("geometry")
        if not geometry:
            continue
        for lng, lat in _iter_coords(geometry):
            min_lng = min(min_lng, lng)
            max_lng = max(max_lng, lng)
            min_lat = min(min_lat, lat)
            max_lat = max(max_lat, lat)
    if min_lng == float("inf"):
        raise ValueError("GeoJSON contains no coordinates.")
    return [min_lng, min_lat, max_lng, max_lat]


def geometry_type(feature: dict[str, Any]) -> str:
    geometry = feature.get("geometry") or {}
    geom_type = geometry.get("type")
    if not geom_type:
        raise ValueError("Feature missing geometry type.")
    return geom_type
