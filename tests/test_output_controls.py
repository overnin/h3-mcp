from __future__ import annotations

import random

from h3_mcp.output_controls import apply_cell_controls, apply_list_controls, apply_sampling


def test_apply_sampling_first() -> None:
    items = [1, 2, 3, 4]
    assert apply_sampling(items, max_items=2, sample="first") == [1, 2]


def test_apply_sampling_random_deterministic() -> None:
    items = [1, 2, 3, 4]
    rng = random.Random(42)
    result = apply_sampling(items, max_items=2, sample="random", rng=rng)
    assert result == [1, 4]


def test_apply_list_controls_summary() -> None:
    items = ["a", "b"]
    assert apply_list_controls(items, return_mode="summary", max_items=1, sample="first") is None


def test_apply_cell_controls_cells() -> None:
    cells = ["a", "b", "c"]
    assert apply_cell_controls(cells, return_mode="cells", max_cells=2, sample="first") == ["a", "b"]
