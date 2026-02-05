from __future__ import annotations

import h3

from h3_mcp.models.schemas import CellsetRef, H3KRingInput
from h3_mcp.tools.neighbors import h3_k_ring


def test_h3_k_ring_cells() -> None:
    cell = h3.latlng_to_cell(37.775, -122.418, 9)
    expected = set(h3.grid_disk(cell, 1))
    payload = H3KRingInput(
        cellset=CellsetRef(cells=[cell]),
        k=1,
        return_mode="cells",
    )
    result = h3_k_ring(payload)
    assert result.ring_cells is not None
    assert set(result.ring_cells) == expected
    assert result.ring_cell_count == len(expected)
