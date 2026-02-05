from __future__ import annotations

import h3

from h3_mcp.models.schemas import H3GeoToCellsInput
from h3_mcp.tools.indexing import h3_geo_to_cells


def test_h3_geo_to_cells_point() -> None:
    lat, lng = 37.775, -122.418
    res = 9
    cell = h3.latlng_to_cell(lat, lng, res)
    geojson = {
        "type": "Feature",
        "properties": {"name": "test"},
        "geometry": {"type": "Point", "coordinates": [lng, lat]},
    }
    payload = H3GeoToCellsInput(geojson=geojson, resolution=res, return_mode="cells")
    result = h3_geo_to_cells(payload)
    assert result.cell_count == 1
    assert result.cells is not None
    assert result.cells[0].cell_id == cell
    assert result.cells[0].source_properties == {"name": "test"}
    assert result.cellset_id is not None
    assert result.bounding_box == [lng, lat, lng, lat]


def test_h3_geo_to_cells_cache_toggle() -> None:
    lat, lng = 37.775, -122.418
    res = 9
    geojson = {
        "type": "Feature",
        "properties": {},
        "geometry": {"type": "Point", "coordinates": [lng, lat]},
    }
    payload = H3GeoToCellsInput(
        geojson=geojson, resolution=res, return_mode="summary", cache_cells=False
    )
    result = h3_geo_to_cells(payload)
    assert result.cellset_id is None
