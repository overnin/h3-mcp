# Solar vs Grid Stress (Synthetic)

This walkthrough demonstrates Scenario 2 from the implementation plan with synthetic points.

## Goal
Find neighborhood-level areas where transformers exist but solar presence is missing.

## Tool Call Sequence
1. `h3_geo_to_cells` on transformer points at `resolution=9`.
2. `h3_geo_to_cells` on solar points at `resolution=9`.
3. `h3_change_resolution` on both outputs to `target_resolution=7`.
4. `h3_compare_sets`:
- `set_a=transformers_res7`
- `set_b=solar_res7`

## Expected Reasoning
- `only_a_count > 0` indicates neighborhoods with transformer presence but no solar cells.
- `overlap_ratio_a` indicates share of transformer neighborhoods with solar overlap.

## Token-Safe Parameters
- Keep all calls at `return_mode="summary"` during normal operation.
- Use `include_cells=true` only when cells are needed for plotting.
