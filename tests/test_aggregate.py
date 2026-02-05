from __future__ import annotations

import h3

from h3_mcp.models.schemas import H3AggregateInput
from h3_mcp.tools.analysis import h3_aggregate


def test_h3_aggregate_sum_mean() -> None:
    cell_a = h3.latlng_to_cell(37.775, -122.418, 9)
    cell_b = h3.latlng_to_cell(37.776, -122.419, 9)
    values_by_cell = {cell_a: {"value": 10.0}, cell_b: {"value": 20.0}}
    target_resolution = 8
    payload = H3AggregateInput(
        values_by_cell=values_by_cell,
        target_resolution=target_resolution,
        aggregations={"value": "sum"},
        return_mode="items",
    )
    result = h3_aggregate(payload)
    parent_map: dict[str, list[float]] = {}
    for cell, value in [(cell_a, 10.0), (cell_b, 20.0)]:
        parent = h3.cell_to_parent(cell, target_resolution)
        parent_map.setdefault(parent, []).append(value)
    expected_sums = {parent: sum(values) for parent, values in parent_map.items()}
    assert result.parent_cells is not None
    for parent_cell in result.parent_cells:
        assert parent_cell.aggregated_values["value"] == expected_sums[parent_cell.cell_id]
