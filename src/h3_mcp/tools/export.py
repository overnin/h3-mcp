from __future__ import annotations

from ..h3_ops import cell_area_km2, cell_to_boundary, cell_to_latlng
from ..models.schemas import H3CellsToGeojsonInput, H3CellsToGeojsonOutput, LatLng
from ..output_controls import apply_sampling
from .cellsets import resolve_cellset


def h3_cells_to_geojson(payload: H3CellsToGeojsonInput) -> H3CellsToGeojsonOutput:
    cells = resolve_cellset(payload.cellset)
    if payload.return_mode == "cells":
        return H3CellsToGeojsonOutput(
            feature_count=len(cells),
            cells=cells,
            features=None,
            summary=f"{len(cells)} cell IDs returned.",
        )

    if payload.return_mode == "summary":
        center = None
        bounding_box = None
        total_area_km2 = None
        summary = f"Generated {len(cells)} hexagonal polygons."

        if cells:
            centers = [cell_to_latlng(c) for c in cells]
            lats = [lat for lat, _ in centers]
            lngs = [lng for _, lng in centers]
            center = LatLng(lat=sum(lats) / len(lats), lng=sum(lngs) / len(lngs))
            bounding_box = [min(lngs), min(lats), max(lngs), max(lats)]
            total_area_km2 = round(cell_area_km2(cells[0]) * len(cells), 2)
            summary = (
                f"Generated {len(cells)} hexagonal polygons covering "
                f"~{total_area_km2} km², centered on ({center.lat:.4f}, {center.lng:.4f})."
            )

        return H3CellsToGeojsonOutput(
            feature_count=len(cells),
            features=None,
            center=center,
            bounding_box=bounding_box,
            total_area_km2=total_area_km2,
            summary=summary,
        )

    features = []
    for cell in cells:
        boundary = cell_to_boundary(cell)
        coordinates = [[(lng, lat) for lat, lng in boundary]]
        coordinates[0].append(coordinates[0][0])
        properties = dict(payload.properties or {})
        if payload.cell_properties and cell in payload.cell_properties:
            properties.update(payload.cell_properties[cell])
        feature = {
            "type": "Feature",
            "properties": properties,
            "geometry": {"type": "Polygon", "coordinates": coordinates},
        }
        features.append(feature)

    if payload.max_features:
        features = apply_sampling(features, payload.max_features, "first")

    return H3CellsToGeojsonOutput(
        feature_count=len(cells),
        features=features,
        summary=f"Generated {len(features)} hexagonal polygons.",
    )
