from __future__ import annotations

import h3

from h3_mcp.models.schemas import CellsetRef, H3DistanceMatrixInput, LabeledCellset
from h3_mcp.tools.analysis import h3_distance_matrix


def test_h3_distance_matrix_basic() -> None:
    origin = h3.latlng_to_cell(37.775, -122.418, 9)
    dest = h3.latlng_to_cell(37.78, -122.41, 9)
    expected = h3.grid_distance(origin, dest)
    payload = H3DistanceMatrixInput(
        origins=LabeledCellset(label="origins", cellset=CellsetRef(cells=[origin])),
        destinations=LabeledCellset(label="destinations", cellset=CellsetRef(cells=[dest])),
        return_mode="items",
    )
    result = h3_distance_matrix(payload)
    assert result.pairs is not None
    assert result.pairs[0].distance_hops == expected
