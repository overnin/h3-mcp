from __future__ import annotations

from ..h3_ops import cell_to_boundary
from ..models.schemas import H3CellsToGeojsonInput, H3CellsToGeojsonOutput
from ..output_controls import apply_sampling
from .cellsets import resolve_cellset


def h3_cells_to_geojson(payload: H3CellsToGeojsonInput) -> H3CellsToGeojsonOutput:
    cells = resolve_cellset(payload.cellset)
    if payload.return_mode == "summary":
        return H3CellsToGeojsonOutput(
            feature_count=len(cells),
            features=None,
            summary=f"Generated {len(cells)} hexagonal polygons.",
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
