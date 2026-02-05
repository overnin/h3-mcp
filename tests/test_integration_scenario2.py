from __future__ import annotations

from h3_mcp.models.schemas import (
    CellsetRef,
    H3ChangeResolutionInput,
    H3CompareSetsInput,
    H3GeoToCellsInput,
    LabeledCellset,
)
from h3_mcp.tools.comparison import h3_compare_sets
from h3_mcp.tools.hierarchy import h3_change_resolution
from h3_mcp.tools.indexing import h3_geo_to_cells


def _point_feature(lat: float, lng: float, props: dict) -> dict:
    return {
        "type": "Feature",
        "properties": props,
        "geometry": {"type": "Point", "coordinates": [lng, lat]},
    }


def test_scenario2_transformers_vs_solar() -> None:
    res_points = 9
    res_neighborhood = 7

    transformer_points = [
        (37.775, -122.418),
        (37.79, -122.45),
    ]
    solar_points = [
        (37.776, -122.418),
    ]

    transformers_geojson = {
        "type": "FeatureCollection",
        "features": [
            _point_feature(lat, lng, {"type": "transformer", "idx": i})
            for i, (lat, lng) in enumerate(transformer_points)
        ],
    }
    solar_geojson = {
        "type": "FeatureCollection",
        "features": [
            _point_feature(lat, lng, {"type": "solar", "idx": i})
            for i, (lat, lng) in enumerate(solar_points)
        ],
    }

    transformers = h3_geo_to_cells(
        H3GeoToCellsInput(geojson=transformers_geojson, resolution=res_points)
    )
    solar = h3_geo_to_cells(H3GeoToCellsInput(geojson=solar_geojson, resolution=res_points))

    transformers_res7 = h3_change_resolution(
        H3ChangeResolutionInput(
            cellset=CellsetRef(cellset_id=transformers.cellset_id),
            target_resolution=res_neighborhood,
        )
    )
    solar_res7 = h3_change_resolution(
        H3ChangeResolutionInput(
            cellset=CellsetRef(cellset_id=solar.cellset_id),
            target_resolution=res_neighborhood,
        )
    )

    result = h3_compare_sets(
        H3CompareSetsInput(
            set_a=LabeledCellset(
                label="transformers",
                cellset=CellsetRef(cellset_id=transformers_res7.cellset_id),
            ),
            set_b=LabeledCellset(
                label="solar",
                cellset=CellsetRef(cellset_id=solar_res7.cellset_id),
            ),
        )
    )

    assert result.set_a_count == 2
    assert result.set_b_count == 1
    assert result.overlap_count == 1
    assert result.only_a_count == 1
    assert result.only_b_count == 0
