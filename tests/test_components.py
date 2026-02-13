from __future__ import annotations

import h3
import pytest

from h3_mcp.models.schemas import CellsetRef, H3ConnectedComponentsInput
from h3_mcp.tools.cellsets import resolve_cellset
from h3_mcp.tools.components import h3_connected_components


def test_single_contiguous_group(cellset_cache) -> None:
    center = h3.latlng_to_cell(52.37, 4.89, 7)
    cells = list(h3.grid_disk(center, 1))
    payload = H3ConnectedComponentsInput(cellset=CellsetRef(cells=cells))
    result = h3_connected_components(payload)
    assert result.total_cells == len(cells)
    assert result.component_count == 1
    assert result.components[0].cell_count == len(cells)
    assert result.components[0].center is not None
    assert result.components[0].bounding_box is not None
    assert result.components[0].total_area_km2 > 0


def test_two_separate_clusters(cellset_cache) -> None:
    cluster_a_center = h3.latlng_to_cell(52.37, 4.89, 9)
    cluster_b_center = h3.latlng_to_cell(40.71, -74.01, 9)
    cluster_a = list(h3.grid_disk(cluster_a_center, 1))
    cluster_b = list(h3.grid_disk(cluster_b_center, 1))
    all_cells = cluster_a + cluster_b
    payload = H3ConnectedComponentsInput(cellset=CellsetRef(cells=all_cells))
    result = h3_connected_components(payload)
    assert result.component_count == 2
    assert result.components[0].cell_count == result.components[1].cell_count
    cellset_a = resolve_cellset(CellsetRef(cellset_id=result.components[0].cellset_id))
    cellset_b = resolve_cellset(CellsetRef(cellset_id=result.components[1].cellset_id))
    assert set(cellset_a) | set(cellset_b) == set(all_cells)


def test_single_cell(cellset_cache) -> None:
    cell = h3.latlng_to_cell(52.37, 4.89, 9)
    payload = H3ConnectedComponentsInput(cellset=CellsetRef(cells=[cell]))
    result = h3_connected_components(payload)
    assert result.total_cells == 1
    assert result.component_count == 1
    assert result.components[0].cell_count == 1


def test_min_cells_filter(cellset_cache) -> None:
    cluster_a_center = h3.latlng_to_cell(52.37, 4.89, 9)
    cluster_a = list(h3.grid_disk(cluster_a_center, 1))  # 7 cells
    single_cell = h3.latlng_to_cell(40.71, -74.01, 9)
    all_cells = cluster_a + [single_cell]
    payload = H3ConnectedComponentsInput(
        cellset=CellsetRef(cells=all_cells), min_cells=2
    )
    result = h3_connected_components(payload)
    assert result.total_cells == len(all_cells)
    assert result.component_count == 1
    assert result.components[0].cell_count == len(cluster_a)


def test_component_cellset_ids_are_valid(cellset_cache) -> None:
    center = h3.latlng_to_cell(52.37, 4.89, 7)
    cells = list(h3.grid_disk(center, 1))
    payload = H3ConnectedComponentsInput(cellset=CellsetRef(cells=cells))
    result = h3_connected_components(payload)
    for comp in result.components:
        resolved = resolve_cellset(CellsetRef(cellset_id=comp.cellset_id))
        assert len(resolved) == comp.cell_count


def test_mixed_resolution_raises(cellset_cache) -> None:
    cell_a = h3.latlng_to_cell(52.37, 4.89, 7)
    cell_b = h3.latlng_to_cell(52.37, 4.89, 9)
    payload = H3ConnectedComponentsInput(cellset=CellsetRef(cells=[cell_a, cell_b]))
    with pytest.raises(ValueError, match="same resolution"):
        h3_connected_components(payload)
