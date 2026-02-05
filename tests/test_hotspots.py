from __future__ import annotations

import h3

from h3_mcp.models.schemas import H3FindHotspotsInput
from h3_mcp.tools.analysis import h3_find_hotspots


def test_h3_find_hotspots_detects_center() -> None:
    center = h3.latlng_to_cell(37.775, -122.418, 9)
    neighbors = h3.grid_disk(center, 1)
    values_by_cell = {cell: 1.0 for cell in neighbors}
    values_by_cell[center] = 10.0
    payload = H3FindHotspotsInput(
        values_by_cell=values_by_cell,
        k=1,
        threshold=1.0,
        return_mode="items",
    )
    result = h3_find_hotspots(payload)
    assert result.hotspots is not None
    assert any(h.cell_id == center for h in result.hotspots)
