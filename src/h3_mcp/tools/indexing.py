from __future__ import annotations

from ..geojson_utils import bounding_box_from_geojson, iter_features
from ..h3_ops import latlng_to_cell, line_to_cells, polygon_to_cells, cell_area_km2
from ..models.schemas import H3GeoToCellsInput, H3GeoToCellsOutput, CellWithSource
from ..output_controls import apply_sampling
from .cellsets import store_cellset


def h3_geo_to_cells(payload: H3GeoToCellsInput) -> H3GeoToCellsOutput:
    cell_sources: dict[str, dict[str, list]] = {}
    cell_ids: set[str] = set()
    feature_count = 0
    geometry_count = 0

    for idx, feature in enumerate(iter_features(payload.geojson)):
        feature_count += 1
        geometry = feature.get("geometry") or {}
        geom_type = geometry.get("type")
        properties = feature.get("properties") or {}

        cells: list[str] = []
        if geom_type == "Point":
            lng, lat = geometry.get("coordinates", [])
            cells = [latlng_to_cell(lat, lng, payload.resolution)]
            geometry_count += 1
        elif geom_type == "MultiPoint":
            for lng, lat in geometry.get("coordinates", []):
                cells.append(latlng_to_cell(lat, lng, payload.resolution))
            geometry_count += len(geometry.get("coordinates", []))
        elif geom_type in {"LineString", "MultiLineString"}:
            cells = line_to_cells(geometry, payload.resolution)
            geometry_count += len(geometry.get("coordinates", []))
        elif geom_type in {"Polygon", "MultiPolygon"}:
            cells = polygon_to_cells(geometry, payload.resolution)
            geometry_count += len(geometry.get("coordinates", []))
        else:
            raise ValueError(f"Unsupported geometry type: {geom_type}")

        for cell_id in cells:
            cell_ids.add(cell_id)
            entry = cell_sources.setdefault(cell_id, {"indices": [], "properties": []})
            entry["indices"].append(idx)
            entry["properties"].append(properties)

    cellset_id = store_cellset(cell_ids) if cell_ids and payload.cache_cells else None
    bounding_box = bounding_box_from_geojson(payload.geojson)
    approx_cell_area = (
        f"{cell_area_km2(next(iter(cell_ids))):.3f} km² per cell" if cell_ids else "0 km² per cell"
    )

    cells_output: list[CellWithSource] | None = None
    if payload.return_mode == "cells":
        cell_objects: list[CellWithSource] = []
        for cell_id in sorted(cell_sources.keys()):
            indices = cell_sources[cell_id]["indices"]
            properties = cell_sources[cell_id]["properties"]
            cell_objects.append(
                CellWithSource(
                    cell_id=cell_id,
                    source_feature_index=indices[0],
                    source_properties=properties[0] if len(properties) == 1 else properties,
                )
            )
        cells_output = apply_sampling(cell_objects, payload.max_cells, payload.sample_cells)

    summary = (
        f"{feature_count} features indexed to {len(cell_ids)} "
        f"unique cells at res {payload.resolution}. "
        f"{geometry_count} geometries processed."
    )

    return H3GeoToCellsOutput(
        cellset_id=cellset_id,
        cell_count=len(cell_ids),
        resolution=payload.resolution,
        approx_cell_area=approx_cell_area,
        bounding_box=bounding_box,
        cells=cells_output,
        summary=summary,
    )
