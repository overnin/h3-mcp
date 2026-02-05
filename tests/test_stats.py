from __future__ import annotations

import h3
import pytest

from h3_mcp.models.schemas import CellsetRef, H3CellStatsInput
from h3_mcp.tools.stats import h3_cell_stats


def test_h3_cell_stats_basic() -> None:
    cell_a = h3.latlng_to_cell(37.775, -122.418, 9)
    cell_b = h3.latlng_to_cell(37.78, -122.41, 9)
    payload = H3CellStatsInput(cellset=CellsetRef(cells=[cell_a, cell_b]))
    result = h3_cell_stats(payload)
    assert result.cell_count == 2
    assert result.resolution == 9
    lat_a, lng_a = h3.cell_to_latlng(cell_a)
    lat_b, lng_b = h3.cell_to_latlng(cell_b)
    assert result.bounding_box == pytest.approx(
        [min(lng_a, lng_b), min(lat_a, lat_b), max(lng_a, lng_b), max(lat_a, lat_b)]
    )
