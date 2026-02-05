# Agent Composition Guide

## Recommended Defaults
- Prefer `return_mode="summary"` for all tools.
- Use `cellset_id` chaining whenever available.
- Set `include_cells=false` unless you need exact geometry outputs.

## Typical Flows
### Coverage gap
1. `h3_geo_to_cells` (area boundary)
2. `h3_geo_to_cells` (service points)
3. `h3_k_ring` (service points)
4. `h3_compare_sets` (area vs service area)

### Multi-source overlap ranking
1. `h3_geo_to_cells` for each source
2. `h3_compare_many` with `matrix_metric="jaccard"`

### Neighborhood roll-up
1. `h3_geo_to_cells`
2. `h3_change_resolution` to coarser level
3. `h3_aggregate`

## Token Safety
- Use `max_cells`, `max_items`, `max_features` when requesting list outputs.
- Use `top_k` on `h3_compare_many` to cap overlap payloads.
- Use GeoJSON export only at final visualization step.

## Error Recovery
- If a `cellset_id` expires, re-run indexing and continue the chain.
- If resolution validation fails, consult `h3://resolution-guide`.
