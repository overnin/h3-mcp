from __future__ import annotations

import time
from typing import Iterable

import h3

from .models.schemas import CellsetRef, H3CompareSetsInput, LabeledCellset
from .tools.comparison import h3_compare_sets


def generate_disk_cells(center_cell: str, k: int) -> list[str]:
    return list(h3.grid_disk(center_cell, k))


def benchmark_compare_sets(cells_a: Iterable[str], cells_b: Iterable[str]) -> float:
    payload = H3CompareSetsInput(
        set_a=LabeledCellset(label="A", cellset=CellsetRef(cells=list(cells_a))),
        set_b=LabeledCellset(label="B", cellset=CellsetRef(cells=list(cells_b))),
        include_cells=False,
    )
    start = time.perf_counter()
    h3_compare_sets(payload)
    end = time.perf_counter()
    return end - start
