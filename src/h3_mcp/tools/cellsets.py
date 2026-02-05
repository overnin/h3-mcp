from __future__ import annotations

from typing import Iterable

from ..cache import CellsetCache, normalize_cells
from ..models.schemas import CellsetRef
from ..runtime import get_cache


def resolve_cellset(cellset: CellsetRef, cache: CellsetCache | None = None) -> list[str]:
    if cellset.cells is not None:
        return normalize_cells(cellset.cells)
    if not cellset.cellset_id:
        raise ValueError("cellset_id is required when cells are not provided.")
    cache = cache or get_cache()
    cells = cache.get_cells(cellset.cellset_id)
    if cells is None:
        raise ValueError(f"Unknown or expired cellset_id: {cellset.cellset_id}")
    return cells


def store_cellset(cells: Iterable[str], cache: CellsetCache | None = None) -> str:
    cache = cache or get_cache()
    return cache.put_cells(cells)
