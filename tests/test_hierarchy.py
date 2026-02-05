from __future__ import annotations

import h3

from h3_mcp.models.schemas import CellsetRef, H3ChangeResolutionInput
from h3_mcp.tools.hierarchy import h3_change_resolution


def test_h3_change_resolution_coarser() -> None:
    cell = h3.latlng_to_cell(37.775, -122.418, 9)
    parent = h3.cell_to_parent(cell, 8)
    payload = H3ChangeResolutionInput(
        cellset=CellsetRef(cells=[cell]),
        target_resolution=8,
        return_mode="cells",
    )
    result = h3_change_resolution(payload)
    assert result.direction == "coarser"
    assert result.output_cell_count == 1
    assert result.cells is not None
    assert result.cells == [parent]
