from __future__ import annotations

import pytest
from pydantic import ValidationError

from h3_mcp.models.schemas import H3GeoToCellsInput


def test_resolution_validation_message() -> None:
    geojson = {
        "type": "Feature",
        "properties": {},
        "geometry": {"type": "Point", "coordinates": [0, 0]},
    }
    with pytest.raises(ValidationError) as excinfo:
        H3GeoToCellsInput(geojson=geojson, resolution=16)
    assert "Resolution must be 0-15" in str(excinfo.value)
