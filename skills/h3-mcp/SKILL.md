---
name: h3-mcp-spatial
description: Orchestrate H3 MCP tools for spatial set comparisons, coverage analysis, aggregation, hotspots, and proximity on GeoJSON datasets with token-safe summaries.
---

# H3 MCP Spatial Orchestration

## When to use this skill
- Use this MCP when you need H3-based spatial reasoning: overlaps, gaps, coverage ratios, multi-dataset ranking, or proximity.
- Use this MCP when inputs are GeoJSON batches or large point sets and you want summaries instead of raw geometry.
- Write code directly when you need exact GIS operations (buffers, projections, topology fixes) or non-H3 geometry.

## Vertical skills

Domain-specific analysis guides that extend this base skill with business vocabulary, resolution defaults, recipes, and interpretation:

| Vertical | Description |
|---|---|
| [`skills/verticals/ev-infrastructure/SKILL.md`](../verticals/ev-infrastructure/SKILL.md) | EV charging deserts, grid-solar mismatch, demand hotspots, charger-substation proximity |
| [`skills/verticals/telecom-coverage/SKILL.md`](../verticals/telecom-coverage/SKILL.md) | Dead-zone detection, multi-operator comparison, signal hotspots, tower siting |
| [`skills/verticals/waste-management/SKILL.md`](../verticals/waste-management/SKILL.md) | Collection coverage gaps, overflow hotspots, illegal dumping clusters, facility proximity, service equity |

## Data layer roles

When planning an analysis, classify each input dataset by its role. The role determines which tools and parameters to apply:

| Role | Description | Typical geometry | Tool pattern |
|------|-------------|------------------|--------------|
| **Boundary** | Defines the analysis area (territory, region, administrative unit) | Polygon | `h3_geo_to_cells` → use as reference set in `h3_compare_sets` |
| **Subject** | The primary entities being analyzed (assets, plots, towers, chargers) | Point or Polygon | `h3_geo_to_cells` → `h3_k_ring` if points need service radius |
| **Comparison** | Layer compared against the subject (risk zones, demand data, competing operators) | Any geometry | `h3_geo_to_cells` → feed into `h3_compare_sets` or `h3_compare_many` |

Not every analysis requires all three roles. Some analyses compare two subject layers directly (e.g., multi-operator comparison). The key rule: if a layer represents point entities with a service radius, apply `h3_k_ring`; if it is a boundary or zone, index it directly.

## MCP tools available
- `h3_geo_to_cells` — index GeoJSON (Point/MultiPoint/LineString/MultiLineString/Polygon/MultiPolygon) to H3 cells.
- `h3_k_ring` — expand cells by k hops (service areas).
- `h3_change_resolution` — move between H3 resolutions.
- `h3_compare_sets` — pairwise overlap metrics and gap sets.
- `h3_compare_many` — N-way overlaps, top-k pairs, optional matrices.
- `h3_cells_to_geojson` — export H3 cells as hex polygons, raw cell IDs, or spatial summary (center, bbox, area).
- `h3_connected_components` — split a cellset into contiguous connected components.
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

## Resolution and scaling guidance

Resolution range is `0–15`. Use `h3://resolution-guide` for full details.

| Res | Cells/km² | Hex area | Typical use |
|-----|-----------|----------|-------------|
| 5   | 4         | 253 km²  | Country/state overview |
| 6   | 25        | 36 km²   | Metro region |
| 7   | 175       | 5.2 km²  | City-wide planning |
| 8   | 1,220     | 0.74 km² | District/neighborhood |
| 9   | 8,540     | 0.11 km² | Block-level / site selection |
| 10  | 59,800    | 0.015 km²| Parcel-level |
| 11  | 418,600   | 0.002 km²| Sub-hectare precision |

**Scaling zones** — estimate total cells as `area_km² × cells/km²` for the chosen resolution:

| Total cells | Zone | Action |
|-------------|------|--------|
| < 5,000     | Fast | Proceed normally |
| 5,000–50,000| Caution | Use summary mode; avoid distance_matrix on full sets |
| > 50,000    | Large | Warn user; propose coarser resolution for overview, then drill down into specific areas at finer resolution |

**k-ring expansion:** Each input cell expands to `3k² + 3k + 1` cells. At k=3, that is 37 cells per input. Multiply input cell count by this factor when estimating output size.

**Drill-down pattern:** Start at coarse resolution (res 6-7) for overview and identification. Then propose to the user a drill-down at finer resolution (res 9-10) on specific areas of interest identified in the overview. Synthesize findings across scales.

- `h3_find_hotspots`: `k` is `1–5`. `threshold` is a z-score (>0).
- `h3_compare_many`: `top_k` controls output size; `return_mode="stats"` returns matrices.
- `h3_aggregate`: target resolution must be coarser or equal to input.

## Gotchas and edge cases
- All cell sets must share the same resolution for `h3_k_ring`, `h3_change_resolution`, and `h3_cell_stats`.
- `h3_compare_many` requires unique labels; `matrix_metric="overlap_ratio"` is directional.
- `h3_geo_to_cells` only supports the GeoJSON geometry types listed above.
- `cellset_id` handles are cached (TTL/LRU) and may expire; re-index if missing.
- `h3_cells_to_geojson` returns hex boundaries, not original geometry. Use `return_mode="cells"` for raw IDs or `"summary"` for center/bbox/area without GeoJSON.
- `h3_distance_matrix` returns hop counts, not kilometers.
- Jumping directly to fine resolution (res 9+) on large areas. Estimate cell count first; use the drill-down pattern for areas > 5,000 km².
- Using the same resolution for overview and detail. Coarse for identification, fine for investigation.
- Ignoring k-ring expansion in cell count estimates. k=3 multiplies input cells by 37x.
- Comparing datasets at mismatched resolutions. All inputs to a comparison tool must share the same resolution.

## Interpreting outputs for reasoning
- `overlap_ratio_a` / `overlap_ratio_b`: asymmetric coverage (A covered by B vs B covered by A).
- `jaccard_index`: symmetric similarity for overlaps.
- `only_a_count` / `only_b_count`: exclusive areas (gaps).
- `top_overlaps[].score`: jaccard or overlap ratio depending on `matrix_metric`.
- `summary` fields are the primary reasoning surface; avoid raw IDs unless required.

## Creating new vertical skills

Add vertical skills to `skills/verticals/<domain>/SKILL.md`. Each vertical extends this base skill and follows this 5-section template:

```markdown
---
name: h3-<vertical-name>
description: One-line description
---

# <Vertical> Analysis

> Extends `skills/h3-mcp/SKILL.md`.

## 1. Domain Context
Business vocabulary mapped to H3 operations. Include a data-layer-roles table:

| Role | Layer name | Geometry | Key attributes | Notes |
|------|-----------|----------|----------------|-------|
| Boundary | ... | Polygon | — | Analysis area |
| Subject | ... | Point/Polygon | ... | Primary entities |
| Comparison | ... | Any | ... | Layer compared against subject |

Which tools matter most for this domain.

## 2. Resolution & Parameter Defaults
Table of analysis types with recommended resolution and reasoning.
k-ring and hotspot parameter defaults tuned for the domain.

## 3. Analytical Recipes
5 numbered recipes. Each recipe contains:
- **Goal** — what question it answers
- **Tool sequence** — ordered tool calls with key parameters
- **Interpretation** — how to read the output in domain terms
- **Extensions** — optional follow-up analyses

## 4. Interpretation Guide
Table mapping output fields to domain-specific meanings and thresholds.

## 5. Anti-Patterns
Bulleted list of domain-specific mistakes to avoid.
```
