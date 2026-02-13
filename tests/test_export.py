from __future__ import annotations

import h3
import pytest

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


def test_geojson_summary_has_spatial_context() -> None:
    cell_a = h3.latlng_to_cell(37.775, -122.418, 9)
    cell_b = h3.latlng_to_cell(37.78, -122.41, 9)
    payload = H3CellsToGeojsonInput(
        cellset=CellsetRef(cells=[cell_a, cell_b]),
        return_mode="summary",
    )
    result = h3_cells_to_geojson(payload)
    assert result.features is None
    assert result.feature_count == 2
    assert result.center is not None
    assert result.bounding_box is not None
    assert result.total_area_km2 is not None
    assert result.total_area_km2 > 0

    lat_a, lng_a = h3.cell_to_latlng(cell_a)
    lat_b, lng_b = h3.cell_to_latlng(cell_b)
    assert result.bounding_box == pytest.approx(
        [min(lng_a, lng_b), min(lat_a, lat_b), max(lng_a, lng_b), max(lat_a, lat_b)]
    )
    assert result.center.lat == pytest.approx((lat_a + lat_b) / 2)
    assert result.center.lng == pytest.approx((lng_a + lng_b) / 2)
    assert "km²" in result.summary
    assert "centered on" in result.summary


def test_geojson_summary_single_cell() -> None:
    cell = h3.latlng_to_cell(37.775, -122.418, 9)
    payload = H3CellsToGeojsonInput(
        cellset=CellsetRef(cells=[cell]),
        return_mode="summary",
    )
    result = h3_cells_to_geojson(payload)
    assert result.feature_count == 1
    assert result.center is not None
    assert result.bounding_box is not None
    assert result.total_area_km2 is not None
    assert result.total_area_km2 > 0
    assert result.features is None


def test_cells_return_mode() -> None:
    cell = h3.latlng_to_cell(37.775, -122.418, 9)
    payload = H3CellsToGeojsonInput(
        cellset=CellsetRef(cells=[cell]),
        return_mode="cells",
    )
    result = h3_cells_to_geojson(payload)
    assert result.cells is not None
    assert cell in result.cells
    assert result.features is None
    assert result.feature_count == 1


def test_geojson_mode_no_spatial_fields() -> None:
    cell = h3.latlng_to_cell(37.775, -122.418, 9)
    payload = H3CellsToGeojsonInput(
        cellset=CellsetRef(cells=[cell]),
        return_mode="geojson",
    )
    result = h3_cells_to_geojson(payload)
    assert result.features is not None
    assert result.center is None
    assert result.bounding_box is None
    assert result.total_area_km2 is None
