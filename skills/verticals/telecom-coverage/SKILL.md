---
name: h3-telecom-coverage
description: Cell tower coverage analysis — dead-zone detection, multi-operator comparison, signal quality hotspots, tower siting optimization, and coverage redundancy audits.
---

# Telecom Coverage Analysis

> Extends `skills/h3-mcp/SKILL.md`.

## 1. Domain Context

| Business concept | H3 operation | Typical data |
|---|---|---|
| Dead zone | Territory minus tower k-ring coverage | Polygon (territory) + Point (tower locations) |
| Multi-operator comparison | N-way comparison of operator coverage footprints | Multiple Point/Polygon datasets per operator |
| Signal quality hotspot | Z-score analysis on signal measurements | Point (measurements) with RSRP/RSRQ attribute |
| Tower siting candidate | Dead-zone cells intersected with demand cells | Derived cellsets from prior analyses |
| Coverage redundancy | Aggregate tower count per cell → find over/under-served | Point (towers) with count attribute |

**Data layer roles:**

| Role | Layer name | Geometry | Key attributes | Notes |
|------|-----------|----------|----------------|-------|
| Boundary | Service territory | Polygon | — | Operator license area or municipality |
| Subject | Tower locations | Point | tower_type (macro/small/micro), height_m | Apply k-ring with type-specific k values |
| Comparison | Signal measurements | Point | rsrp_dbm, rsrq_db | For quality hotspot analysis |
| Comparison | Population / subscriber density | Point/Polygon | population, subscribers | For demand-based siting |
| Comparison | Competing operator towers | Point | operator | For N-way coverage comparison |

Key tools: `h3_geo_to_cells`, `h3_k_ring`, `h3_change_resolution`, `h3_compare_sets`, `h3_compare_many`, `h3_cells_to_geojson`, `h3_connected_components`, `h3_cell_stats`, `h3_aggregate`, `h3_find_hotspots`, `h3_distance_matrix`.

## 2. Resolution & Parameter Defaults

| Analysis type | Resolution | Reasoning |
|---|---|---|
| Regional dead-zone scan | 7 | ~5 km² hex — matches macro-cell coverage radius |
| Urban tower coverage | 9 | ~0.1 km² hex — small-cell and micro-cell range |
| Signal quality mapping | 8 | ~0.7 km² hex — balances measurement density with spatial detail |
| Tower siting candidates | 9 | Fine enough for site-selection precision |
| Coverage density audit | 7–8 | Neighborhood-level for capacity planning |

| Parameter | Default | Notes |
|---|---|---|
| `k` (k-ring for macro tower) | 3 at res 7 | ≈5 km radius — typical macro-cell coverage |
| `k` (k-ring for small cell) | 2 at res 9 | ≈300 m radius — typical small-cell range |
| `k` (hotspot neighborhood) | 2 | Local signal quality clustering |
| `threshold` (hotspot z-score) | 1.5 | Flags significant signal anomalies |
| `max_distance` (distance_matrix) | 15 | ≈2.2 km at res 9 — useful for inter-tower spacing analysis |
| `min_cells` (connected_components) | 5 | Filters small dead-zone fragments |

**Scaling note:** A regional territory at res 7 with k=3 expansion produces ~37x the input tower count in coverage cells. For 500 towers in a 10,000 km² region: territory alone is ~1.75M cells at res 7. Start with a representative sub-region or reduce k. At res 9 (urban analysis), limit to areas < 100 km² to stay in the Caution zone.

## 3. Analytical Recipes

### Recipe 1: Dead Zone Detection

**Goal:** Find contiguous areas within a territory that are outside tower coverage range.

**Tool sequence:**
1. `h3_geo_to_cells` — index territory polygon at res 7 → `territory_id`
2. `h3_geo_to_cells` — index tower locations at res 7 → `towers_id`
3. `h3_k_ring` — expand towers with `k=3` → `coverage_id`
4. `h3_compare_sets` — `set_a=territory_id`, `set_b=coverage_id`
5. `h3_connected_components` — on `only_a` cells, `min_cells=5`

**Interpretation:**
- `only_a_count` = total dead-zone cells
- `overlap_ratio_a` = fraction of territory with coverage (target: >0.95)
- Connected components rank dead zones by size — largest = highest priority

**Extensions:**
- `h3_cells_to_geojson` on largest component for planning maps
- `h3_distance_matrix` from dead-zone centroids to nearest tower for gap severity

### Recipe 2: Multi-Operator Coverage Comparison

**Goal:** Compare coverage footprints across operators to identify exclusive and shared areas.

**Tool sequence:**
1. `h3_geo_to_cells` — index each operator's tower locations at res 8
2. `h3_k_ring` — expand each operator's towers with `k=2` → coverage per operator
3. `h3_compare_many` — all operator coverages, `matrix_metric="jaccard"`, `top_k=5`

**Interpretation:**
- `top_overlaps` = operator pairs with most shared coverage
- Low jaccard = operators cover different areas (roaming opportunity)
- `union_count` vs individual counts = total population coverage vs single-operator coverage

**Extensions:**
- `h3_compare_sets` on specific pair for detailed exclusive/shared breakdown
- `h3_cells_to_geojson` on `only_a` cells for operator-exclusive areas

### Recipe 3: Signal Quality Hotspot Mapping

**Goal:** Identify areas with anomalously strong or weak signal measurements.

**Tool sequence:**
1. `h3_geo_to_cells` — index signal measurement points at res 8 → `measurements_id`
2. `h3_aggregate` — roll up RSRP values by cell, `op="mean"` → average signal per hex
3. `h3_find_hotspots` — `k=2`, `threshold=1.5`

**Interpretation:**
- Hot cells = areas with signal strength significantly above neighborhood average (good coverage, potential over-investment)
- Cold cells = areas with signal significantly below average (quality dead zones)
- Cold cells clustered near territory edges = expected; cold cells in urban core = problem

**Extensions:**
- Cross-reference cold cells with Recipe 1 dead zones for combined coverage + quality view
- `h3_cell_stats` on cold clusters for area and location context

### Recipe 4: Tower Siting Optimization

**Goal:** Identify candidate locations for new towers by intersecting dead zones with demand areas.

**Tool sequence:**
1. Run Recipe 1 to get dead-zone cells → `dead_zones_id`
2. `h3_geo_to_cells` — index population or subscriber density data at res 9 → `demand_id`
3. `h3_compare_sets` — `set_a=dead_zones_id`, `set_b=demand_id`
4. `h3_connected_components` — on `overlap` cells, `min_cells=3`

**Interpretation:**
- `overlap_count` = dead-zone cells that also have demand → highest-priority candidates
- Connected components identify distinct candidate clusters for tower placement
- Largest cluster center = best single-tower location for maximum impact

**Extensions:**
- `h3_distance_matrix` from candidate clusters to existing towers for spacing validation
- `h3_cells_to_geojson` on candidate clusters for site acquisition maps

### Recipe 5: Coverage Density & Redundancy Audit

**Goal:** Find areas with too many or too few towers for capacity planning.

**Tool sequence:**
1. `h3_geo_to_cells` — index all tower locations at res 9
2. `h3_aggregate` — roll up tower counts to res 7, `op="sum"` → towers per neighborhood
3. `h3_find_hotspots` — `k=2`, `threshold=1.5`

**Interpretation:**
- Hot cells = neighborhoods with significantly more towers than average (potential over-provisioning, consolidation candidates)
- Cold cells = neighborhoods with fewer towers than average (capacity risk as demand grows)
- Combine with subscriber data for towers-per-subscriber ratio analysis

**Extensions:**
- `h3_compare_sets` of cold cells vs high-demand areas for capacity gap analysis
- `h3_cell_stats` on hot clusters for area context on consolidation potential

## 4. Interpretation Guide

| Output field | Domain meaning | Threshold guidance |
|---|---|---|
| `only_a_count` (dead zone) | Territory cells without coverage | >5% of territory = coverage gap |
| `overlap_ratio_a` (coverage) | Fraction of territory covered | <0.95 = below typical regulatory target |
| `jaccard_index` (operators) | Coverage similarity between operators | >0.5 = high overlap; <0.2 = complementary |
| `z_score` (signal hotspot) | Signal strength deviation from local mean | <-1.5 = quality dead zone; >1.5 = over-served |
| `overlap_count` (siting) | Dead-zone cells with demand | Higher = more impactful tower placement |
| `component_count` (dead zones) | Number of distinct gap areas | Few large > many small for prioritization |
| `avg_distance` (tower spacing) | Mean hops between towers | <3 at res 9 ≈ under-spaced; >8 = potential gap |
| `unreachable_count` (spacing) | Towers beyond max spacing | Any >0 = isolated tower, verify coverage |

## 5. Anti-Patterns

- **Using fixed k-ring for all tower types.** Macro towers (k=3 at res 7) and small cells (k=2 at res 9) have very different coverage radii. Match k and resolution to tower class.
- **Comparing operators at mismatched resolutions.** All operator datasets must be at the same resolution before `h3_compare_many`. Index at the same res or `h3_change_resolution` first.
- **Interpreting signal hotspots without domain context.** A "cold" signal cell near a territory edge is expected (less infrastructure), not necessarily a problem. Focus on cold cells in urban/suburban cores.
- **Skipping connected_components on dead zones.** Raw dead-zone cell counts are misleading — one 50-cell contiguous gap is more actionable than fifty scattered single-cell gaps.
- **Over-optimizing tower placement from hex centroids.** H3 provides candidate zones, not GPS coordinates. Site acquisition requires terrain, zoning, and RF propagation analysis beyond H3.
- **Running distance_matrix on full tower inventory without max_distance.** Large tower sets produce huge matrices; always bound with `max_distance` and use `return_mode="summary"`.
