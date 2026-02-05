from __future__ import annotations

import h3

from h3_mcp.models.schemas import CellsetRef, H3CellsToGeojsonInput
from h3_mcp.tools.export import h3_cells_to_geojson


def test_h3_cells_to_geojson() -> None:
    cell = h3.latlng_to_cell(37.775, -122.418, 9)
    payload = H3CellsToGeojsonInput(
        cellset=CellsetRef(cells=[cell]),
        return_mode="geojson",
    )
    result = h3_cells_to_geojson(payload)
    assert result.features is not None
    assert result.feature_count == 1
    feature = result.features[0]
    assert feature["geometry"]["type"] == "Polygon"
    coords = feature["geometry"]["coordinates"][0]
    assert coords[0] == coords[-1]
