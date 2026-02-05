from __future__ import annotations

import h3

from h3_mcp.benchmarks import generate_disk_cells


def test_generate_disk_cells_size() -> None:
    center = h3.latlng_to_cell(37.775, -122.418, 9)
    cells = generate_disk_cells(center, 1)
    assert len(cells) == 7
