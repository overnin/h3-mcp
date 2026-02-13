from __future__ import annotations

from collections import deque

from ..h3_ops import cell_area_km2, cell_to_latlng, get_resolution, grid_disk
from ..models.schemas import (
    ConnectedComponent,
    H3ConnectedComponentsInput,
    H3ConnectedComponentsOutput,
    LatLng,
)
from .cellsets import resolve_cellset, store_cellset


def _find_components(cells: list[str]) -> list[list[str]]:
    unvisited = set(cells)
    components: list[list[str]] = []
    while unvisited:
        seed = next(iter(unvisited))
        component: list[str] = []
        queue = deque([seed])
        while queue:
            current = queue.popleft()
            if current not in unvisited:
                continue
            unvisited.discard(current)
            component.append(current)
            for neighbor in grid_disk(current, 1):
                if neighbor in unvisited:
                    queue.append(neighbor)
        components.append(component)
    return components


def _compute_component(
    component_id: int, cells: list[str]
) -> ConnectedComponent:
    centers = [cell_to_latlng(c) for c in cells]
    lats = [lat for lat, _ in centers]
    lngs = [lng for _, lng in centers]
    center = LatLng(lat=sum(lats) / len(lats), lng=sum(lngs) / len(lngs))
    bounding_box = [min(lngs), min(lats), max(lngs), max(lats)]
    total_area_km2 = round(cell_area_km2(cells[0]) * len(cells), 2)
    cellset_id = store_cellset(cells)
    return ConnectedComponent(
        component_id=component_id,
        cell_count=len(cells),
        center=center,
        bounding_box=bounding_box,
        total_area_km2=total_area_km2,
        cellset_id=cellset_id,
    )


def h3_connected_components(
    payload: H3ConnectedComponentsInput,
) -> H3ConnectedComponentsOutput:
    cells = resolve_cellset(payload.cellset)
    if not cells:
        return H3ConnectedComponentsOutput(
            total_cells=0,
            component_count=0,
            components=[],
            summary="0 cells, no connected components.",
        )

    resolutions = {get_resolution(c) for c in cells}
    if len(resolutions) != 1:
        raise ValueError("All input cells must share the same resolution.")

    raw_components = _find_components(cells)
    filtered = [c for c in raw_components if len(c) >= payload.min_cells]
    filtered.sort(key=len, reverse=True)

    components = [
        _compute_component(i, comp) for i, comp in enumerate(filtered)
    ]

    parts: list[str] = []
    for comp in components[:5]:
        parts.append(
            f"{comp.cell_count} cells centered on "
            f"({comp.center.lat:.4f}, {comp.center.lng:.4f})"
        )
    detail = ", ".join(parts)
    remaining = len(components) - 5
    if remaining > 0:
        detail += f", ... and {remaining} smaller components"
    summary = (
        f"{len(cells)} cells split into {len(components)} connected components: {detail}."
        if components
        else f"{len(cells)} cells, no components after min_cells={payload.min_cells} filter."
    )

    return H3ConnectedComponentsOutput(
        total_cells=len(cells),
        component_count=len(components),
        components=components,
        summary=summary,
    )
