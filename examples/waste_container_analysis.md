# Waste Container Analysis (Synthetic)

> **See also:** This coverage-gap pattern is generalized in three vertical skills:
> - [`skills/verticals/waste-management/SKILL.md`](../skills/verticals/waste-management/SKILL.md) — Recipe 1 (Collection Coverage Gap Detection) — the direct generalization of this example
> - [`skills/verticals/ev-infrastructure/SKILL.md`](../skills/verticals/ev-infrastructure/SKILL.md) — Recipe 1 (Charging Desert Detection)
> - [`skills/verticals/telecom-coverage/SKILL.md`](../skills/verticals/telecom-coverage/SKILL.md) — Recipe 1 (Dead Zone Detection)

This walkthrough demonstrates Scenario 1 from the implementation plan with synthetic data.

## Goal
Estimate which city cells are outside a one-hop service area around container locations.

## Tool Call Sequence
1. `h3_geo_to_cells` on city boundary polygon at `resolution=9`.
2. `h3_geo_to_cells` on container points at `resolution=9`.
3. `h3_k_ring` on container cellset with `k=1`.
4. `h3_compare_sets`:
- `set_a=city_boundary_cells`
- `set_b=container_service_cells`

## Expected Reasoning
- `overlap_count` approximates covered city cells.
- `only_a_count` approximates uncovered city cells.
- `overlap_ratio_a` provides coverage ratio for city area.

## Token-Safe Parameters
- Use `return_mode="summary"` for all calls except debugging.
- Set `include_cells=false` in `h3_compare_sets`.
