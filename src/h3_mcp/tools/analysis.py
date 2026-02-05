from __future__ import annotations

from collections import defaultdict
import math
from typing import cast

from ..h3_ops import cell_to_parent, get_resolution, grid_disk, grid_distance
from ..models.schemas import (
    AggregatedParentCell,
    H3AggregateInput,
    H3AggregateOutput,
    H3DistanceMatrixInput,
    H3DistanceMatrixOutput,
    H3FindHotspotsInput,
    H3FindHotspotsOutput,
    HotspotCell,
    DistancePair,
)
from ..output_controls import apply_list_controls
from .cellsets import resolve_cellset, store_cellset


def _aggregate_values_from_payload(payload: H3AggregateInput) -> dict[str, dict[str, float]]:
    cellset = payload.cellset
    cell_values = payload.cell_values
    values_by_cell = payload.values_by_cell

    if cell_values is not None:
        return {entry.cell_id: entry.values for entry in cell_values}
    if values_by_cell is None:
        raise ValueError("values_by_cell is required when cell_values is not provided.")
    if cellset is None:
        return values_by_cell
    allowed = set(resolve_cellset(cellset))
    return {cell_id: values for cell_id, values in values_by_cell.items() if cell_id in allowed}


def _hotspot_values_from_payload(payload: H3FindHotspotsInput) -> dict[str, float]:
    cellset = payload.cellset
    cell_values = payload.cell_values
    values_by_cell = payload.values_by_cell

    if cell_values is not None:
        return {entry.cell_id: entry.value for entry in cell_values}
    if values_by_cell is None:
        raise ValueError("values_by_cell is required when cell_values is not provided.")
    if cellset is None:
        return values_by_cell
    allowed = set(resolve_cellset(cellset))
    return {cell_id: value for cell_id, value in values_by_cell.items() if cell_id in allowed}


def h3_aggregate(payload: H3AggregateInput) -> H3AggregateOutput:
    values_map = _aggregate_values_from_payload(payload)
    if not values_map:
        return H3AggregateOutput(
            input_cell_count=0,
            parent_cell_count=0,
            parent_cellset_id=None,
            parent_cells=[] if payload.return_mode == "items" else None,
            summary="No values provided for aggregation.",
        )

    resolutions = {get_resolution(cell_id) for cell_id in values_map}
    if len(resolutions) != 1:
        raise ValueError("All input cells must share the same resolution.")
    input_resolution = resolutions.pop()
    if payload.target_resolution > input_resolution:
        raise ValueError("Cannot aggregate to a finer resolution.")

    parent_values: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    child_counts: dict[str, int] = defaultdict(int)

    for cell_id, values in values_map.items():
        parent = (
            cell_id
            if payload.target_resolution == input_resolution
            else cell_to_parent(cell_id, payload.target_resolution)
        )
        child_counts[parent] += 1
        for field, value in values.items():
            parent_values[parent][field].append(value)

    parent_cells: list[AggregatedParentCell] = []
    for parent_id, field_values in parent_values.items():
        aggregated: dict[str, float] = {}
        for field, op in payload.aggregations.items():
            field_series = cast(list[float], field_values.get(field, []))
            if op == "sum":
                aggregated[field] = float(sum(field_series))
            elif op == "mean":
                aggregated[field] = (
                    float(sum(field_series) / len(field_series)) if field_series else 0.0
                )
            elif op == "max":
                aggregated[field] = float(max(field_series)) if field_series else 0.0
            elif op == "min":
                aggregated[field] = float(min(field_series)) if field_series else 0.0
            elif op == "count":
                aggregated[field] = float(len(field_series))
            else:
                raise ValueError(f"Unsupported aggregation op: {op}")
        parent_cells.append(
            AggregatedParentCell(
                cell_id=parent_id,
                child_count=child_counts[parent_id],
                aggregated_values=aggregated,
            )
        )

    parent_cellset_id = store_cellset(parent_values.keys()) if parent_values else None
    parent_cells_output = apply_list_controls(
        parent_cells,
        payload.return_mode,
        payload.max_items,
        payload.sample_items,
    )

    summary = (
        f"{len(values_map)} cells aggregated to {len(parent_values)} parent cells "
        f"at res {payload.target_resolution}."
    )

    return H3AggregateOutput(
        input_cell_count=len(values_map),
        parent_cell_count=len(parent_values),
        parent_cellset_id=parent_cellset_id,
        parent_cells=parent_cells_output,
        summary=summary,
    )


def h3_find_hotspots(payload: H3FindHotspotsInput) -> H3FindHotspotsOutput:
    values_map = _hotspot_values_from_payload(payload)
    if not values_map:
        return H3FindHotspotsOutput(
            hotspot_count=0,
            coldspot_count=0,
            hotspot_cellset_id=None,
            coldspot_cellset_id=None,
            hotspots=[] if payload.return_mode == "items" else None,
            coldspots=[] if payload.return_mode == "items" else None,
            summary="No values provided for hotspot detection.",
        )

    resolutions = {get_resolution(cell_id) for cell_id in values_map}
    if len(resolutions) != 1:
        raise ValueError("All input cells must share the same resolution.")

    hotspots: list[HotspotCell] = []
    coldspots: list[HotspotCell] = []

    for cell_id, value in values_map.items():
        neighbors = grid_disk(cell_id, payload.k)
        neighbor_values = [values_map[n] for n in neighbors if n in values_map]
        if not neighbor_values:
            continue
        mean = sum(neighbor_values) / len(neighbor_values)
        variance = sum((v - mean) ** 2 for v in neighbor_values) / len(neighbor_values)
        std = math.sqrt(variance)
        z_score = (value - mean) / std if std > 0 else 0.0

        if z_score >= payload.threshold:
            hotspots.append(HotspotCell(cell_id=cell_id, value=value, z_score=z_score))
        elif z_score <= -payload.threshold:
            coldspots.append(HotspotCell(cell_id=cell_id, value=value, z_score=z_score))

    hotspot_cellset_id = store_cellset([h.cell_id for h in hotspots]) if hotspots else None
    coldspot_cellset_id = store_cellset([c.cell_id for c in coldspots]) if coldspots else None

    hotspots_output = apply_list_controls(
        hotspots, payload.return_mode, payload.max_items, payload.sample_items
    )
    coldspots_output = apply_list_controls(
        coldspots, payload.return_mode, payload.max_items, payload.sample_items
    )

    summary = (
        f"Found {len(hotspots)} hotspots and {len(coldspots)} coldspots "
        f"at threshold {payload.threshold}."
    )

    return H3FindHotspotsOutput(
        hotspot_count=len(hotspots),
        coldspot_count=len(coldspots),
        hotspot_cellset_id=hotspot_cellset_id,
        coldspot_cellset_id=coldspot_cellset_id,
        hotspots=hotspots_output,
        coldspots=coldspots_output,
        summary=summary,
    )


def h3_distance_matrix(payload: H3DistanceMatrixInput) -> H3DistanceMatrixOutput:
    origins = resolve_cellset(payload.origins.cellset)
    destinations = resolve_cellset(payload.destinations.cellset)

    if not origins or not destinations:
        return H3DistanceMatrixOutput(
            pair_count=0,
            avg_distance=0.0,
            max_distance=0,
            unreachable_count=len(origins),
            pairs=[] if payload.return_mode == "items" else None,
            summary="No origins or destinations provided.",
        )

    pairs: list[DistancePair] = []
    total_distance = 0
    reachable = 0
    unreachable_count = 0
    max_distance = 0

    for origin in origins:
        best_distance: int | None = None
        best_destination: str | None = None
        for dest in destinations:
            distance = grid_distance(origin, dest)
            if payload.max_distance is not None and distance > payload.max_distance:
                continue
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_destination = dest
        if best_distance is None:
            unreachable_count += 1
            continue
        if best_destination is None:
            unreachable_count += 1
            continue
        pairs.append(
            DistancePair(
                origin=origin,
                nearest_destination=best_destination,
                distance_hops=best_distance,
            )
        )
        total_distance += best_distance
        reachable += 1
        max_distance = max(max_distance, best_distance)

    avg_distance = total_distance / reachable if reachable else 0.0
    pairs_output = apply_list_controls(
        pairs, payload.return_mode, payload.max_items, payload.sample_items
    )

    summary = (
        f"Average distance from {payload.origins.label} to nearest {payload.destinations.label}: "
        f"{avg_distance:.2f} hops. {unreachable_count} origins unreachable."
    )

    return H3DistanceMatrixOutput(
        pair_count=len(pairs),
        avg_distance=avg_distance,
        max_distance=max_distance,
        unreachable_count=unreachable_count,
        pairs=pairs_output,
        summary=summary,
    )
