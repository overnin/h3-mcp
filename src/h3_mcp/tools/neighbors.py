from __future__ import annotations

from ..h3_ops import average_edge_length_km, grid_disk, get_resolution
from ..models.schemas import H3KRingInput, H3KRingOutput
from ..output_controls import apply_cell_controls
from .cellsets import resolve_cellset, store_cellset


def h3_k_ring(payload: H3KRingInput) -> H3KRingOutput:
    cells = resolve_cellset(payload.cellset)
    if not cells:
        return H3KRingOutput(
            input_cell_count=0,
            ring_cell_count=0,
            k=payload.k,
            approx_radius_km=0.0,
            ring_cellset_id=None,
            ring_cells=[] if payload.return_mode == "cells" else None,
            summary="No input cells provided.",
        )

    resolutions = {get_resolution(cell) for cell in cells}
    if len(resolutions) != 1:
        raise ValueError("All input cells must share the same resolution.")
    res = resolutions.pop()

    ring_cells_set: set[str] = set()
    for cell in cells:
        ring_cells_set.update(grid_disk(cell, payload.k))

    ring_cells = sorted(ring_cells_set)
    ring_cellset_id = store_cellset(ring_cells) if ring_cells else None
    approx_radius_km = payload.k * average_edge_length_km(res) * 1.732

    ring_cells_output = apply_cell_controls(
        ring_cells,
        payload.return_mode,
        payload.max_cells,
        payload.sample_cells,
    )

    summary = (
        f"{len(cells)} input cells expanded to {len(ring_cells)} ring cells "
        f"(k={payload.k}, ~{approx_radius_km:.2f} km radius)"
    )

    return H3KRingOutput(
        input_cell_count=len(cells),
        ring_cell_count=len(ring_cells),
        k=payload.k,
        approx_radius_km=approx_radius_km,
        ring_cellset_id=ring_cellset_id,
        ring_cells=ring_cells_output,
        summary=summary,
    )
