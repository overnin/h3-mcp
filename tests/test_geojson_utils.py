from __future__ import annotations

from h3_mcp.geojson_utils import bounding_box_from_geojson, iter_features


def test_iter_features_single() -> None:
    feature = {"type": "Feature", "geometry": {"type": "Point", "coordinates": [1, 2]}}
    assert list(iter_features(feature)) == [feature]


def test_bounding_box_from_geojson() -> None:
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [1, 2]}},
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-1, 0], [2, 5]],
                },
            },
        ],
    }
    assert bounding_box_from_geojson(geojson) == [-1, 0, 2, 5]
