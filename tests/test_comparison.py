from __future__ import annotations

import pytest

from h3_mcp.models.schemas import CellsetRef, H3CompareManyInput, H3CompareSetsInput, LabeledCellset
from h3_mcp.tools.comparison import h3_compare_many, h3_compare_sets


def test_compare_sets_uses_cache(cellset_cache) -> None:
    set_a_id = cellset_cache.put_cells(["a", "b", "c"])
    payload = H3CompareSetsInput(
        set_a=LabeledCellset(label="A", cellset=CellsetRef(cellset_id=set_a_id)),
        set_b=LabeledCellset(label="B", cellset=CellsetRef(cells=["b", "c", "d"])),
        include_cells=False,
    )
    result = h3_compare_sets(payload)
    assert result.overlap_count == 2
    assert result.only_a_count == 1
    assert result.only_b_count == 1
    assert result.overlap_cells is None
    assert result.overlap_cellset_id is not None
    assert cellset_cache.get_cells(result.overlap_cellset_id) == ["b", "c"]


def test_compare_sets_include_cells(cellset_cache) -> None:
    payload = H3CompareSetsInput(
        set_a=LabeledCellset(label="A", cellset=CellsetRef(cells=["x", "y"])),
        set_b=LabeledCellset(label="B", cellset=CellsetRef(cells=["y", "z"])),
        include_cells=True,
    )
    result = h3_compare_sets(payload)
    assert result.overlap_cells == ["y"]
    assert result.only_a_cells == ["x"]
    assert result.only_b_cells == ["z"]


def test_compare_many_stats_and_cellsets(cellset_cache) -> None:
    payload = H3CompareManyInput(
        sets=[
            LabeledCellset(label="A", cellset=CellsetRef(cells=["a", "b"])),
            LabeledCellset(label="B", cellset=CellsetRef(cells=["b", "c"])),
            LabeledCellset(label="C", cellset=CellsetRef(cells=["d"])),
        ],
        matrix_metric="jaccard",
        include_cells=True,
        return_mode="stats",
    )
    result = h3_compare_many(payload)
    assert len(result.set_stats) == 3
    assert result.overlap_counts is not None
    assert result.overlap_matrix is not None
    assert result.overlap_counts[0][1] == 1
    assert result.overlap_counts[0][2] == 0
    assert result.overlap_cellsets is not None
    assert len(result.overlap_cellsets) == 1
    overlap_entry = result.overlap_cellsets[0]
    assert overlap_entry.a == "A"
    assert overlap_entry.b == "B"
    assert cellset_cache.get_cells(overlap_entry.cellset_id) == ["b"]


def test_compare_many_overlap_ratio_directional(cellset_cache) -> None:
    payload = H3CompareManyInput(
        sets=[
            LabeledCellset(label="A", cellset=CellsetRef(cells=["a", "b", "c"])),
            LabeledCellset(label="B", cellset=CellsetRef(cells=["a"])),
        ],
        matrix_metric="overlap_ratio",
        include_cells=False,
        return_mode="stats",
        top_k=2,
    )
    result = h3_compare_many(payload)
    assert result.overlap_matrix is not None
    assert result.overlap_matrix[0][1] == pytest.approx(1 / 3)
    assert result.overlap_matrix[1][0] == pytest.approx(1.0)
    assert result.top_overlaps[0].a == "B"
    assert result.top_overlaps[0].b == "A"
    assert result.top_overlaps[0].score == 1.0
