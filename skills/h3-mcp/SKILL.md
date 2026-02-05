---
name: h3-mcp-spatial
description: Orchestrate H3 MCP tools for spatial set comparisons, coverage analysis, aggregation, hotspots, and proximity on GeoJSON datasets with token-safe summaries.
---

# H3 MCP Spatial Orchestration

## When to use this skill
- Use this MCP when you need H3-based spatial reasoning: overlaps, gaps, coverage ratios, multi-dataset ranking, or proximity.
- Use this MCP when inputs are GeoJSON batches or large point sets and you want summaries instead of raw geometry.
- Write code directly when you need exact GIS operations (buffers, projections, topology fixes) or non-H3 geometry.

## MCP tools available
- `h3_geo_to_cells` — index GeoJSON (Point/MultiPoint/LineString/MultiLineString/Polygon/MultiPolygon) to H3 cells.
- `h3_k_ring` — expand cells by k hops (service areas).
- `h3_change_resolution` — move between H3 resolutions.
- `h3_compare_sets` — pairwise overlap metrics and gap sets.
- `h3_compare_many` — N-way overlaps, top-k pairs, optional matrices.
- `h3_cells_to_geojson` — export H3 cells as hex polygons.
- `h3_cell_stats` — resolution, contiguity, bounding box, area.
- `h3_aggregate` — roll up numeric values to coarser parents.
- `h3_find_hotspots` — z-score hotspots/coldspots by neighborhood.
- `h3_distance_matrix` — nearest-destination hop distances.
- Resource: `h3://resolution-guide` — resolution sizes and usage.

## Token-safe workflow defaults
- Prefer `cellset_id` inputs/outputs and keep `cache_cells=true`.
- Use `return_mode="summary"` (or `"stats"` if you need matrices).
- Keep `include_cells=false`; request cells only when you must visualize.
- Cap outputs with `max_cells`, `max_items`, `max_features`, and `top_k`.

## Common workflow patterns

### Coverage gap analysis
1. `h3_geo_to_cells` on service points at a shared resolution.
2. `h3_k_ring` to build service areas.
3. `h3_geo_to_cells` on demand or boundary areas at the same resolution.
4. `h3_compare_sets` with `set_a=demand`, `set_b=service`.
5. Interpret `only_a_count` as uncovered demand.

### Multi-dataset overlap ranking
1. `h3_geo_to_cells` for each dataset at a shared resolution.
2. `h3_compare_many` with `matrix_metric="jaccard"` and `top_k`.

### Neighborhood roll-up and aggregation
1. Index points or polygons at res 8–9.
2. `h3_change_resolution` to res 6–7 if needed.
3. `h3_aggregate` with `values_by_cell` or `cell_values`.

### Hotspot detection
1. `h3_geo_to_cells` for locations and attach numeric values per cell.
2. `h3_find_hotspots` with `k=1..3` and `threshold≈1.5`.

### Proximity to nearest destination
1. Index origins and destinations at the same resolution.
2. `h3_distance_matrix` with `max_distance` to bound runtime.
3. Use `avg_distance` and `unreachable_count` to reason.

## Resolution and parameter guidance
- Resolution range is `0–15`. Use `h3://resolution-guide` for scale.
- Res 4–5: city-wide planning. Res 6–7: districts/neighborhoods. Res 8–9: blocks.
- `h3_k_ring`: `k` is `1–50`. k=1 at res 9 ≈ 150m radius.
- `h3_find_hotspots`: `k` is `1–5`. `threshold` is a z-score (>0).
- `h3_compare_many`: `top_k` controls output size; `return_mode="stats"` returns matrices.
- `h3_aggregate`: target resolution must be coarser or equal to input.

## Gotchas and edge cases
- All cell sets must share the same resolution for `h3_k_ring`, `h3_change_resolution`, and `h3_cell_stats`.
- `h3_compare_many` requires unique labels; `matrix_metric="overlap_ratio"` is directional.
- `h3_geo_to_cells` only supports the GeoJSON geometry types listed above.
- `cellset_id` handles are cached (TTL/LRU) and may expire; re-index if missing.
- `h3_cells_to_geojson` returns hex boundaries, not original geometry.
- `h3_distance_matrix` returns hop counts, not kilometers.

## Interpreting outputs for reasoning
- `overlap_ratio_a` / `overlap_ratio_b`: asymmetric coverage (A covered by B vs B covered by A).
- `jaccard_index`: symmetric similarity for overlaps.
- `only_a_count` / `only_b_count`: exclusive areas (gaps).
- `top_overlaps[].score`: jaccard or overlap ratio depending on `matrix_metric`.
- `summary` fields are the primary reasoning surface; avoid raw IDs unless required.
