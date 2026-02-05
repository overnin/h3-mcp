from __future__ import annotations

from collections import deque

from ..h3_ops import cell_area_km2, cell_to_latlng, grid_disk, get_resolution
from ..models.schemas import H3CellStatsInput, H3CellStatsOutput, LatLng
from .cellsets import resolve_cellset


def _is_contiguous(cells: list[str]) -> bool:
    if not cells:
        return False
    cell_set = set(cells)
    visited = set()
    queue = deque([cells[0]])
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        for neighbor in grid_disk(current, 1):
            if neighbor in cell_set and neighbor not in visited:
                queue.append(neighbor)
    return len(visited) == len(cell_set)


def h3_cell_stats(payload: H3CellStatsInput) -> H3CellStatsOutput:
    cells = resolve_cellset(payload.cellset)
    if not cells:
        return H3CellStatsOutput(
            cell_count=0,
            resolution=0,
            avg_area_km2=0.0,
            total_area_km2=0.0,
            bounding_box=[0, 0, 0, 0],
            center=LatLng(lat=0.0, lng=0.0),
            is_contiguous=False,
            summary="No cells provided.",
        )

    resolutions = {get_resolution(cell) for cell in cells}
    if len(resolutions) != 1:
        raise ValueError("All input cells must share the same resolution.")
    resolution = resolutions.pop()

    centers = [cell_to_latlng(cell) for cell in cells]
    latitudes = [lat for lat, _ in centers]
    longitudes = [lng for _, lng in centers]
    bounding_box = [min(longitudes), min(latitudes), max(longitudes), max(latitudes)]
    center = LatLng(lat=sum(latitudes) / len(latitudes), lng=sum(longitudes) / len(longitudes))

    avg_area_km2 = cell_area_km2(cells[0])
    total_area_km2 = avg_area_km2 * len(cells)
    contiguous = _is_contiguous(cells)

    summary = (
        f"{len(cells)} cells at res {resolution}, covering ~{total_area_km2:.2f} km² "
        f"centered on ({center.lat:.4f}, {center.lng:.4f})"
    )

    return H3CellStatsOutput(
        cell_count=len(cells),
        resolution=resolution,
        avg_area_km2=avg_area_km2,
        total_area_km2=total_area_km2,
        bounding_box=bounding_box,
        center=center,
        is_contiguous=contiguous,
        summary=summary,
    )
