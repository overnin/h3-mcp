from __future__ import annotations

from typing import Any, Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator, BeforeValidator

def _parse_resolution(value: Any) -> int:
    try:
        res = int(value)
    except (TypeError, ValueError):
        raise ValueError("Resolution must be an integer between 0 and 15.")
    if res < 0 or res > 15:
        raise ValueError(
            "Resolution must be 0-15. Use the resolution guide resource for reference."
        )
    return res


Resolution = Annotated[int, BeforeValidator(_parse_resolution)]
KRing = Annotated[int, Field(ge=1, le=50)]
BoundingBox = Annotated[list[float], Field(min_length=4, max_length=4)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CellsetRef(StrictModel):
    cellset_id: str | None = Field(
        default=None,
        description="Content-addressed handle to a cached cellset (preferred).",
    )
    cells: list[str] | None = Field(
        default=None,
        description="Raw H3 cell IDs (avoid for large inputs).",
    )
    label: str | None = Field(default=None, description="Optional label for reporting.")

    @model_validator(mode="after")
    def _require_cells_or_id(self) -> "CellsetRef":
        if not self.cellset_id and not self.cells:
            raise ValueError("Provide cellset_id or cells.")
        return self


class CellOutputControls(StrictModel):
    return_mode: Literal["summary", "stats", "cells"] = Field(
        default="summary",
        description="Controls payload size and verbosity.",
    )
    max_cells: int | None = Field(
        default=None,
        ge=1,
        description="Hard cap for returned cells when return_mode='cells'.",
    )
    sample_cells: Literal["first", "random"] = Field(
        default="first",
        description="Sampling strategy if max_cells is applied.",
    )


class ListOutputControls(StrictModel):
    return_mode: Literal["summary", "stats", "items"] = Field(
        default="summary",
        description="Controls payload size and verbosity.",
    )
    max_items: int | None = Field(
        default=None,
        ge=1,
        description="Hard cap for returned items when return_mode='items'.",
    )
    sample_items: Literal["first", "random"] = Field(
        default="first",
        description="Sampling strategy if max_items is applied.",
    )


class GeojsonOutputControls(StrictModel):
    return_mode: Literal["summary", "geojson"] = Field(
        default="geojson",
        description="Return GeoJSON or summary only.",
    )
    max_features: int | None = Field(
        default=None,
        ge=1,
        description="Hard cap for returned GeoJSON features.",
    )


class CellWithSource(StrictModel):
    cell_id: str
    source_feature_index: int
    source_properties: dict[str, Any] | list[dict[str, Any]]


class LabeledCellset(StrictModel):
    label: str
    cellset: CellsetRef


class H3GeoToCellsInput(CellOutputControls):
    geojson: dict[str, Any] = Field(
        description="GeoJSON FeatureCollection or Feature."
    )
    cache_cells: bool = Field(
        default=True,
        description="Whether to store the resulting cellset in cache.",
    )
    resolution: Resolution


class H3GeoToCellsOutput(StrictModel):
    cellset_id: str | None = None
    cell_count: int
    resolution: Resolution
    approx_cell_area: str
    bounding_box: BoundingBox
    cells: list[CellWithSource] | None = None
    summary: str


class H3KRingInput(CellOutputControls):
    cellset: CellsetRef
    k: KRing


class H3KRingOutput(StrictModel):
    input_cell_count: int
    ring_cell_count: int
    k: KRing
    approx_radius_km: float
    ring_cellset_id: str | None = None
    ring_cells: list[str] | None = None
    summary: str


class H3ChangeResolutionInput(CellOutputControls):
    cellset: CellsetRef
    target_resolution: Resolution


class H3ChangeResolutionOutput(StrictModel):
    input_resolution: Resolution
    target_resolution: Resolution
    input_cell_count: int
    output_cell_count: int
    direction: Literal["coarser", "finer"]
    cellset_id: str | None = None
    cells: list[str] | None = None
    summary: str


class H3CompareSetsInput(StrictModel):
    set_a: LabeledCellset
    set_b: LabeledCellset
    include_cells: bool = Field(
        default=False,
        description="Whether to return overlap/only cell lists.",
    )


class H3CompareSetsOutput(StrictModel):
    set_a_label: str
    set_b_label: str
    set_a_count: int
    set_b_count: int
    overlap_count: int
    only_a_count: int
    only_b_count: int
    overlap_ratio_a: float
    overlap_ratio_b: float
    jaccard_index: float
    overlap_cellset_id: str | None = None
    only_a_cellset_id: str | None = None
    only_b_cellset_id: str | None = None
    overlap_cells: list[str] | None = None
    only_a_cells: list[str] | None = None
    only_b_cells: list[str] | None = None
    summary: str


class H3CompareManyInput(StrictModel):
    sets: list[LabeledCellset] = Field(min_length=2)
    matrix_metric: Literal["jaccard", "overlap_ratio"] = "jaccard"
    include_cells: bool = False
    return_mode: Literal["summary", "stats"] = "summary"
    top_k: int = Field(default=5, ge=1, description="Top overlap pairs to return.")


class SetStats(StrictModel):
    label: str
    cell_count: int


class OverlapPair(StrictModel):
    a: str
    b: str
    overlap_count: int
    score: float


class OverlapCellset(StrictModel):
    a: str
    b: str
    cellset_id: str


class H3CompareManyOutput(StrictModel):
    set_stats: list[SetStats]
    overlap_counts: list[list[int]] | None = None
    overlap_matrix: list[list[float]] | None = None
    top_overlaps: list[OverlapPair]
    overlap_cellsets: list[OverlapCellset] | None = None
    summary: str


class H3CellsToGeojsonInput(GeojsonOutputControls):
    cellset: CellsetRef
    properties: dict[str, Any] | None = None
    cell_properties: dict[str, dict[str, Any]] | None = None


class H3CellsToGeojsonOutput(StrictModel):
    feature_count: int
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[dict[str, Any]] | None = None
    summary: str


class LatLng(StrictModel):
    lat: float
    lng: float


class H3CellStatsInput(StrictModel):
    cellset: CellsetRef


class H3CellStatsOutput(StrictModel):
    cell_count: int
    resolution: Resolution
    avg_area_km2: float
    total_area_km2: float
    bounding_box: BoundingBox
    center: LatLng
    is_contiguous: bool
    summary: str


AggregationOp = Literal["sum", "mean", "max", "min", "count"]
HotspotK = Annotated[int, Field(ge=1, le=5)]


class CellNumericValues(StrictModel):
    cell_id: str
    values: dict[str, float]


class CellNumericValue(StrictModel):
    cell_id: str
    value: float


class H3AggregateInput(ListOutputControls):
    cellset: CellsetRef | None = None
    cell_values: list[CellNumericValues] | None = None
    values_by_cell: dict[str, dict[str, float]] | None = None
    target_resolution: Resolution
    aggregations: dict[str, AggregationOp]

    @model_validator(mode="after")
    def _require_values(self) -> "H3AggregateInput":
        has_inline = self.cell_values is not None
        has_ref = self.values_by_cell is not None
        if has_inline and has_ref:
            raise ValueError("Provide cell_values or (cellset + values_by_cell), not both.")
        if has_inline:
            return self
        if not self.values_by_cell:
            raise ValueError("Provide cell_values or values_by_cell.")
        return self


class AggregatedParentCell(StrictModel):
    cell_id: str
    child_count: int
    aggregated_values: dict[str, float]


class H3AggregateOutput(StrictModel):
    input_cell_count: int
    parent_cell_count: int
    parent_cellset_id: str | None = None
    parent_cells: list[AggregatedParentCell] | None = None
    summary: str


class H3FindHotspotsInput(ListOutputControls):
    cellset: CellsetRef | None = None
    cell_values: list[CellNumericValue] | None = None
    values_by_cell: dict[str, float] | None = None
    k: HotspotK
    threshold: float = Field(default=1.5, gt=0)

    @model_validator(mode="after")
    def _require_values(self) -> "H3FindHotspotsInput":
        has_inline = self.cell_values is not None
        has_ref = self.values_by_cell is not None
        if has_inline and has_ref:
            raise ValueError("Provide cell_values or (cellset + values_by_cell), not both.")
        if has_inline:
            return self
        if not self.values_by_cell:
            raise ValueError("Provide cell_values or values_by_cell.")
        return self


class HotspotCell(StrictModel):
    cell_id: str
    value: float
    z_score: float


class H3FindHotspotsOutput(StrictModel):
    hotspot_count: int
    coldspot_count: int
    hotspot_cellset_id: str | None = None
    coldspot_cellset_id: str | None = None
    hotspots: list[HotspotCell] | None = None
    coldspots: list[HotspotCell] | None = None
    summary: str


class H3DistanceMatrixInput(ListOutputControls):
    origins: LabeledCellset
    destinations: LabeledCellset
    max_distance: int | None = Field(default=None, ge=1)


class DistancePair(StrictModel):
    origin: str
    nearest_destination: str
    distance_hops: int


class H3DistanceMatrixOutput(StrictModel):
    pair_count: int
    avg_distance: float
    max_distance: int
    unreachable_count: int
    pairs: list[DistancePair] | None = None
    summary: str
