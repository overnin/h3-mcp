from __future__ import annotations

from typing import Literal

from ..h3_ops import cell_to_children, cell_to_parent, compact_cells, get_resolution
from ..models.schemas import H3ChangeResolutionInput, H3ChangeResolutionOutput
from ..output_controls import apply_cell_controls
from .cellsets import resolve_cellset, store_cellset


def h3_change_resolution(payload: H3ChangeResolutionInput) -> H3ChangeResolutionOutput:
    cells = resolve_cellset(payload.cellset)
    if not cells:
        return H3ChangeResolutionOutput(
            input_resolution=payload.target_resolution,
            target_resolution=payload.target_resolution,
            input_cell_count=0,
            output_cell_count=0,
            direction="coarser",
            cellset_id=None,
            cells=[] if payload.return_mode == "cells" else None,
            summary="No input cells provided.",
        )

    resolutions = {get_resolution(cell) for cell in cells}
    if len(resolutions) != 1:
        raise ValueError("All input cells must share the same resolution.")
    input_resolution = resolutions.pop()

    output_cells: set[str] = set()
    direction: Literal["coarser", "finer"]
    if payload.target_resolution > input_resolution:
        direction = "finer"
        for cell in cells:
            output_cells.update(cell_to_children(cell, payload.target_resolution))
    elif payload.target_resolution < input_resolution:
        direction = "coarser"
        for cell in cells:
            output_cells.add(cell_to_parent(cell, payload.target_resolution))
        output_cells = set(compact_cells(output_cells))
    else:
        direction = "coarser"
        output_cells = set(cells)

    output_cells_sorted = sorted(output_cells)
    cellset_id = store_cellset(output_cells_sorted) if output_cells_sorted else None
    output_cells_payload = apply_cell_controls(
        output_cells_sorted,
        payload.return_mode,
        payload.max_cells,
        payload.sample_cells,
    )

    summary = (
        f"{len(cells)} cells at res {input_resolution} → {len(output_cells)} cells "
        f"at res {payload.target_resolution}"
    )

    return H3ChangeResolutionOutput(
        input_resolution=input_resolution,
        target_resolution=payload.target_resolution,
        input_cell_count=len(cells),
        output_cell_count=len(output_cells),
        direction=direction,
        cellset_id=cellset_id,
        cells=output_cells_payload,
        summary=summary,
    )
