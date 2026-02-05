from __future__ import annotations

import h3

from h3_mcp.models.schemas import (
    CellsetRef,
    H3CompareSetsInput,
    H3GeoToCellsInput,
    H3KRingInput,
    LabeledCellset,
)
from h3_mcp.tools.comparison import h3_compare_sets
from h3_mcp.tools.indexing import h3_geo_to_cells
from h3_mcp.tools.neighbors import h3_k_ring


def _city_boundary_geojson() -> dict:
    return {
        "type": "Feature",
        "properties": {"name": "Test City"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-122.42, 37.77],
                    [-122.41, 37.77],
                    [-122.41, 37.78],
                    [-122.42, 37.78],
                    [-122.42, 37.77],
                ]
            ],
        },
    }


def _container_points_geojson(center_cell: str) -> dict:
    lat, lng = h3.cell_to_latlng(center_cell)
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": 1},
                "geometry": {"type": "Point", "coordinates": [lng, lat]},
            }
        ],
    }


def test_scenario1_basic_flow() -> None:
    resolution = 9
    boundary = _city_boundary_geojson()
    boundary_cells = h3_geo_to_cells(
        H3GeoToCellsInput(geojson=boundary, resolution=resolution)
    )
    assert boundary_cells.cellset_id is not None

    center_cell = h3.latlng_to_cell(37.775, -122.418, resolution)
    containers = _container_points_geojson(center_cell)
    container_cells = h3_geo_to_cells(
        H3GeoToCellsInput(geojson=containers, resolution=resolution)
    )
    assert container_cells.cellset_id is not None

    ring = h3_k_ring(
        H3KRingInput(cellset=CellsetRef(cellset_id=container_cells.cellset_id), k=1)
    )
    assert ring.ring_cellset_id is not None

    compare = h3_compare_sets(
        H3CompareSetsInput(
            set_a=LabeledCellset(
                label="city", cellset=CellsetRef(cellset_id=boundary_cells.cellset_id)
            ),
            set_b=LabeledCellset(
                label="coverage", cellset=CellsetRef(cellset_id=ring.ring_cellset_id)
            ),
            include_cells=False,
        )
    )
    assert compare.overlap_count <= compare.set_a_count
