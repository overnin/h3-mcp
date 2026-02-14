---
name: h3-ev-infrastructure
description: EV charging coverage gaps, grid-solar mismatch, demand hotspots, charger-substation proximity, and multi-operator overlap analysis.
---

# EV Infrastructure Analysis

> Extends `skills/h3-mcp/SKILL.md`.

## 1. Domain Context

| Business concept | H3 operation | Typical data |
|---|---|---|
| Charging desert | Demand boundary minus charger k-ring coverage | Polygon (service area) + Point (charger locations) |
| Grid stress zone | Transformer cells with no solar overlap | Point (transformers) + Point/Polygon (solar installs) |
| Demand hotspot | High-value cells by registered EV count | Point (EV registrations) with numeric attribute |
| Charger-substation proximity | Hop distance from chargers to nearest substation | Point (chargers) + Point (substations) |
| Operator coverage overlap | N-way comparison of operator footprints | Multiple Point/Polygon datasets per operator |

**Data layer roles:**

| Role | Layer name | Geometry | Key attributes | Notes |
|------|-----------|----------|----------------|-------|
| Boundary | Service territory | Polygon | — | Municipal or utility service area |
| Subject | Charger locations | Point | operator, power_kw | Apply k-ring (k=2 at res 9) for service radius |
| Subject | Transformers / substations | Point | capacity_kva | Grid infrastructure |
| Comparison | EV registrations / demand | Point | count, vehicle_type | Numeric attribute for aggregation |
| Comparison | Solar installations | Point/Polygon | capacity_kw | For grid-solar mismatch |
| Comparison | Competing operator locations | Point | operator | For N-way operator comparison |

Key tools: `h3_geo_to_cells`, `h3_k_ring`, `h3_change_resolution`, `h3_compare_sets`, `h3_compare_many`, `h3_find_hotspots`, `h3_distance_matrix`.

## 2. Resolution & Parameter Defaults

| Analysis type | Resolution | Reasoning |
|---|---|---|
| City-wide charging desert | 7 | ~5 km² hex — matches municipal planning zones |
| Neighborhood charger coverage | 9 | ~0.1 km² hex — walkable service radius |
| Grid-solar mismatch | 7 | Neighborhood-level infrastructure comparison |
| Demand hotspot | 8–9 | Block-level granularity for siting decisions |
| Charger-substation proximity | 9 | Fine enough for distance precision |

| Parameter | Default | Notes |
|---|---|---|
| `k` (k-ring for charger service area) | 2 at res 9 | ≈300 m radius — typical EV driver walk distance |
| `k` (hotspot neighborhood) | 2 | Captures local demand clustering |
| `threshold` (hotspot z-score) | 1.5 | Flags statistically significant demand peaks |
| `max_distance` (distance_matrix) | 10 | ≈1.5 km at res 9 — reasonable charger-to-grid distance |

**Scaling note:** A city service territory at res 9 typically produces 10,000–80,000 cells. For city-wide analysis, start at res 7 (Caution zone), identify gaps, then drill down to res 9 on specific neighborhoods. Avoid res 9 on territories > 500 km².

## 3. Analytical Recipes

### Recipe 1: Charging Desert Detection

**Goal:** Identify areas within a service territory that lack charger coverage.

**Tool sequence:**
1. `h3_geo_to_cells` — index service territory polygon at res 9 → `territory_id`
2. `h3_geo_to_cells` — index charger point locations at res 9 → `chargers_id`
3. `h3_k_ring` — expand chargers with `k=2` → `service_area_id`
4. `h3_compare_sets` — `set_a=territory_id`, `set_b=service_area_id`
5. `h3_connected_components` — on `only_a` cells to find contiguous desert clusters

**Interpretation:**
- `only_a_count` = number of underserved cells (charging deserts)
- `overlap_ratio_a` = fraction of territory covered by existing chargers
- Connected components reveal distinct desert zones ranked by area

**Extensions:**
- Feed desert cells into `h3_find_hotspots` with population data to prioritize by demand
- Use `h3_cells_to_geojson` on largest component for stakeholder maps

### Recipe 2: Grid Stress vs Solar Capacity Mismatch

**Goal:** Find neighborhoods with grid transformer infrastructure but no solar presence.

**Tool sequence:**
1. `h3_geo_to_cells` — index transformer points at res 9 → `transformers_id`
2. `h3_geo_to_cells` — index solar installation points at res 9 → `solar_id`
3. `h3_change_resolution` — both to res 7 for neighborhood view → `trans_res7`, `solar_res7`
4. `h3_compare_sets` — `set_a=trans_res7`, `set_b=solar_res7`

**Interpretation:**
- `only_a_count` = neighborhoods with grid stress but no solar offset
- `overlap_ratio_a` = share of grid-stressed neighborhoods with solar coverage
- High `only_a_count` signals solar deployment opportunities

**Extensions:**
- `h3_cell_stats` on the `only_a` set for area and bounding box
- `h3_cells_to_geojson` for visualization of mismatch zones

### Recipe 3: Demand Hotspot Identification

**Goal:** Find statistically significant clusters of EV charging demand.

**Tool sequence:**
1. `h3_geo_to_cells` — index EV registration points at res 8 → `demand_id`
2. `h3_aggregate` — roll up registration counts to res 7 → aggregated demand per neighborhood
3. `h3_find_hotspots` — `k=2`, `threshold=1.5`

**Interpretation:**
- Hot cells = neighborhoods with demand significantly above local average
- Cold cells = areas with surprisingly low demand (possible data gaps or satisfied demand)
- `z_score` magnitude indicates strength of the signal

**Extensions:**
- Cross-reference hot cells with Recipe 1 desert zones for maximum-impact siting
- `h3_distance_matrix` from hotspot cells to existing chargers to confirm underservice

### Recipe 4: Charger-to-Substation Proximity

**Goal:** Assess how far existing or planned chargers are from grid substations.

**Tool sequence:**
1. `h3_geo_to_cells` — index charger locations at res 9 → `chargers_id`
2. `h3_geo_to_cells` — index substation locations at res 9 → `substations_id`
3. `h3_distance_matrix` — `origins=chargers_id`, `destinations=substations_id`, `max_distance=10`

**Interpretation:**
- `avg_distance` = mean hops to nearest substation (multiply by ~150 m at res 9)
- `unreachable_count` = chargers beyond 10-hop radius — may face costly grid connections
- Per-origin distances identify chargers needing infrastructure investment

**Extensions:**
- Filter unreachable origins and visualize with `h3_cells_to_geojson`
- `h3_cell_stats` on unreachable charger cells for geographic context

### Recipe 5: Multi-Operator Coverage Overlap

**Goal:** Compare coverage footprints across charging network operators.

**Tool sequence:**
1. `h3_geo_to_cells` — index each operator's locations at res 8, label by operator name
2. `h3_compare_many` — all operator cellsets, `matrix_metric="jaccard"`, `top_k=5`

**Interpretation:**
- `top_overlaps` = most overlapping operator pairs (potential partnership or competition)
- Low jaccard between operators = complementary coverage (good for riders, bad for competition)
- `union_count` vs individual counts = total market coverage vs redundancy

**Extensions:**
- `h3_compare_sets` on specific operator pair for detailed gap analysis
- `h3_connected_components` on union set to identify isolated coverage islands

## 4. Interpretation Guide

| Output field | Domain meaning | Threshold guidance |
|---|---|---|
| `only_a_count` (desert) | Cells in territory without charger coverage | >20% of territory = critical gap |
| `overlap_ratio_a` (coverage) | Share of territory served | <0.7 = insufficient network |
| `only_a_count` (grid-solar) | Grid-stressed neighborhoods without solar | Any >0 = deployment opportunity |
| `z_score` (hotspot) | Demand intensity vs neighbors | >1.5 = significant hot, <-1.5 = significant cold |
| `avg_distance` (proximity) | Mean hops to nearest substation | >5 hops at res 9 ≈ 750 m = expensive connection |
| `unreachable_count` | Chargers beyond max grid distance | Any >0 needs infrastructure review |
| `jaccard_index` (operators) | Coverage similarity between operators | >0.3 = significant overlap |
| `component_count` (deserts) | Number of distinct gap zones | Multiple small = scattered; 1 large = systemic |

## 5. Anti-Patterns

- **Mixing resolutions across operator datasets.** Always index all operators at the same resolution before `h3_compare_many`.
- **Using res 9 for city-wide desert detection.** Produces too many cells; use res 7 for city-wide, res 9 for neighborhood drill-down.
- **Interpreting hop distance as meters directly.** Multiply by hex edge length for the resolution (≈150 m at res 9, ≈600 m at res 7).
- **Skipping k-ring for point chargers.** A single point occupies one cell; `h3_k_ring` models the actual service radius.
- **Running `h3_compare_many` with >10 datasets without `top_k`.** Output grows quadratically; always set `top_k` to cap results.
- **Forgetting `cache_cells=true`.** Without caching, downstream tools cannot reference prior cellsets by handle.
