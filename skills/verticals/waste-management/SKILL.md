---
name: h3-waste-management
description: Waste collection coverage gaps, overflow hotspots, illegal dumping clusters, facility proximity, and service equity analysis.
---

# Waste Management Analysis

> Extends `skills/h3-mcp/SKILL.md`.

## 1. Domain Context

| Business concept | H3 operation | Typical data |
|---|---|---|
| Collection coverage gap | Service zone minus container k-ring coverage | Polygon (zone) + Point (containers) |
| Overflow hotspot | Complaint aggregation + z-score detection | Point (311 complaints) with count/date |
| Illegal dumping cluster | Dump report connected components vs disposal coverage | Point (dump reports) + Point (facilities) |
| Transfer station catchment | Hop distance from containers to nearest facility | Point (containers) + Point (facilities) |
| Service equity | N-way comparison of coverage across demographic zones | Multiple Polygon datasets (zones) + Point (containers) |

**Data layer roles:**

| Role | Layer name | Geometry | Key attributes | Notes |
|------|-----------|----------|----------------|-------|
| Boundary | Service zone / collection district | Polygon | zone_id | Analysis area; ward or collection district |
| Subject | Container locations | Point | type, capacity_liters | Apply k-ring (k=1 at res 9) for walk radius |
| Subject | Transfer stations / disposal facilities | Point | facility_type, capacity_tonnes | For proximity and catchment analysis |
| Comparison | Overflow reports / complaints | Point | date, complaint_type | From 311 or sensor alerts |
| Comparison | Illegal dump reports | Point | date, severity | From enforcement or citizen reporting |
| Comparison | Demographic / neighborhood zones | Polygon | population, income_bracket | Census data for equity analysis |

Key tools: `h3_geo_to_cells`, `h3_k_ring`, `h3_change_resolution`, `h3_compare_sets`, `h3_compare_many`, `h3_connected_components`, `h3_find_hotspots`, `h3_aggregate`, `h3_distance_matrix`.

## 2. Resolution & Parameter Defaults

| Analysis type | Resolution | Reasoning |
|---|---|---|
| City-wide coverage gap | 7 | ~5 km² hex — matches collection zone scale |
| Neighborhood service detail | 9 | ~0.1 km² hex — walkable distance to container |
| Overflow/complaint hotspot | 8 | ~0.7 km² hex — balances complaint density with spatial signal |
| Facility catchment/proximity | 8 | District-level for transfer station analysis |
| Service equity comparison | 7 | Aligns with census/demographic zone scale |

| Parameter | Default | Notes |
|---|---|---|
| `k` (container walk radius) | 1 at res 9 | ~150 m — typical walking distance to a waste container |
| `k` (facility catchment) | 3 at res 8 | ~2.5 km — driving catchment for transfer station |
| `k` (hotspot neighborhood) | 2 | Local clustering for complaints/overflow |
| `threshold` (hotspot z-score) | 1.5 | Flags significant overflow or dumping clusters |
| `max_distance` (distance_matrix) | 15 at res 8 | ~12 km — max reasonable travel to transfer station |
| `min_cells` (connected_components) | 3 | Filters single-cell noise from gap and dump detection |

**Scaling note:** A city of 200 km² at res 9 produces ~1.7M cells — always start city-wide analysis at res 7 (~35,000 cells). The "container k-ring trap": 10,000 containers with k=1 at res 9 = ~70,000 service cells (7 cells each), manageable in Caution zone. But k=2 would produce ~130,000 cells, pushing into Large zone. Rule: res 7 + k=1 for city-wide overview, then res 9 + k=1 for neighborhood drill-down on areas < 50 km².

## 3. Analytical Recipes

### Recipe 1: Collection Coverage Gap Detection

**Goal:** Find areas within a service zone that lack container coverage.

**Tool sequence:**
1. `h3_geo_to_cells` — index service zone polygon at res 9 → `zone_id`
2. `h3_geo_to_cells` — index container point locations at res 9 → `containers_id`
3. `h3_k_ring` — expand containers with `k=1` → `service_area_id`
4. `h3_compare_sets` — `set_a=zone_id`, `set_b=service_area_id`
5. `h3_connected_components` — on `only_a` cells, `min_cells=3`

**Interpretation:**
- `only_a_count` = number of underserved cells (collection gaps)
- `overlap_ratio_a` = fraction of zone served by containers — the headline KPI
- Connected components reveal whether gaps are a few large clusters (systematic under-investment) or many scattered cells (normal edge effects)

**Extensions:**
- Feed gap cells into `h3_find_hotspots` with population data to prioritize by demand
- Use `h3_cells_to_geojson` on largest component for stakeholder maps
- Cross-reference with Recipe 2 to find gaps that also have overflow complaints

### Recipe 2: Overflow Risk Hotspot Mapping

**Goal:** Identify statistically significant clusters of overflow complaints or sensor alerts.

**Tool sequence:**
1. `h3_geo_to_cells` — index overflow complaint points at res 8 → `complaints_id`
2. `h3_aggregate` — roll up complaint counts to res 7, `op="sum"` → overflow density per neighborhood
3. `h3_find_hotspots` — `k=2`, `threshold=1.5`

**Interpretation:**
- Hot cells = neighborhoods with overflow complaints significantly above city average — need more capacity or higher collection frequency
- Cold cells = unusually quiet areas — verify if data gap or genuinely well-served
- `z_score` magnitude indicates urgency: >2.5 = critical, immediate action needed

**Extensions:**
- Cross-reference hot cells with Recipe 1 gaps — hotspots that are also coverage gaps are highest priority
- `h3_cell_stats` on hot clusters for area and location context
- Where IoT fill-level sensors are deployed, substitute `fill_pct` for complaint counts

### Recipe 3: Illegal Dumping Cluster Detection

**Goal:** Find contiguous clusters of illegal dumping and assess proximity to legitimate disposal facilities.

**Tool sequence:**
1. `h3_geo_to_cells` — index illegal dump report points at res 8 → `dumps_id`
2. `h3_connected_components` — on dump cells, `min_cells=3` → identified clusters
3. `h3_geo_to_cells` — index disposal facility points at res 8 → `disposal_id`
4. `h3_compare_sets` — `set_a=dumps_id`, `set_b=disposal_coverage`

**Interpretation:**
- `only_a_count` (dump clusters outside disposal range) = dumping likely driven by lack of access — fix is infrastructure
- `overlap_count` (dump clusters near existing disposal) = dumping despite access — fix is enforcement or education
- The ratio between these two numbers guides the policy response

**Extensions:**
- `h3_distance_matrix` from dump cluster centroids to nearest facility for severity assessment
- `h3_cells_to_geojson` on clusters for enforcement patrol maps
- Cross-reference with Recipe 1 gaps — dump clusters overlapping coverage gaps = access-driven problem

### Recipe 4: Transfer Station Catchment & Proximity

**Goal:** Assess how far containers are from transfer stations and identify underserved catchments.

**Tool sequence:**
1. `h3_geo_to_cells` — index container locations at res 8 → `containers_id`
2. `h3_geo_to_cells` — index transfer station / facility points at res 8 → `facilities_id`
3. `h3_distance_matrix` — `origins=containers_id`, `destinations=facilities_id`, `max_distance=15`

**Interpretation:**
- `avg_distance` = mean hops to nearest facility (multiply by ~800 m at res 8)
- `unreachable_count` = containers beyond 15-hop radius (~12 km) — candidates for a new transfer station or satellite facility
- Per-origin distances identify which container clusters face the longest haul distances

**Extensions:**
- `h3_cells_to_geojson` on unreachable containers for facility planning maps
- `h3_cell_stats` on unreachable container cells for geographic context
- `h3_k_ring` on facilities with `k=3` at res 8 and `h3_compare_sets` against city boundary for overall catchment coverage

### Recipe 5: Service Equity Across Neighborhoods

**Goal:** Compare waste collection coverage across demographic zones to assess equitable service distribution.

**Tool sequence:**
1. `h3_geo_to_cells` — index container points at res 9 → `containers_id`
2. `h3_k_ring` — expand containers with `k=1` → `service_id`
3. `h3_change_resolution` — service cells to res 7 → `service_res7`
4. `h3_geo_to_cells` — index each demographic zone polygon at res 7, label by zone name
5. `h3_compare_many` — all zone cellsets vs `service_res7`, `matrix_metric="overlap_ratio"`, `top_k=5`

**Interpretation:**
- `overlap_ratio` per zone = service coverage fraction for that neighborhood
- Zones with low `overlap_ratio` and high population or low income = equity concern
- `top_overlaps` reveals which zones share similar service levels — clusters of underserved zones indicate systemic patterns

**Extensions:**
- `h3_cells_to_geojson` on lowest-coverage zone for stakeholder maps
- Drill down to res 9 on equity-gap zones for detailed container placement planning
- Cross-reference with Recipe 2 overflow hotspots to show disparity in both access and service quality

## 4. Interpretation Guide

| Output field | Domain meaning | Threshold guidance |
|---|---|---|
| `only_a_count` (coverage gap) | Zone cells without container coverage | >15% of zone = service gap requiring attention |
| `overlap_ratio_a` (coverage) | Fraction of zone served by containers | <0.80 = below typical municipal service target |
| `z_score` (overflow hotspot) | Complaint intensity vs local average | >1.5 = significant; >2.5 = critical |
| `z_score` (coldspot) | Unusually low complaints | <-1.5 = verify if data gap or genuinely well-served |
| `component_count` (dump clusters) | Number of distinct illegal dumping zones | Few large = systemic; many small = scattered nuisance |
| `avg_distance` (facility proximity) | Mean hops to nearest transfer station | >8 at res 8 ≈ 6.5 km = consider closer facility |
| `unreachable_count` (facility) | Containers beyond max facility distance | Any >0 = disposal access desert |
| `overlap_ratio` (equity) | Coverage level per demographic zone | Variance >0.15 across zones = equity concern |

## 5. Anti-Patterns

- **Using k=2+ for container walk radius.** Waste containers have ~150 m walk radius (k=1 at res 9), much smaller than EV chargers or cell towers. k=2 overstates coverage and hides real gaps.
- **Confusing container count with total capacity.** One 5,000L underground container is not equivalent to five 240L street bins. When aggregating, use `capacity_liters` as the value attribute, not feature count, unless specifically analyzing container density.
- **Using res 9 for city-wide analysis without drill-down.** 10,000 containers x k=1 at res 9 = ~70,000 cells. Start at res 7 for city-wide overview, then drill down to res 9 on identified problem areas < 50 km².
- **Treating 311 complaint coordinates as precise locations.** Complaints are often geocoded to the nearest intersection or block centroid. Use res 8 (not res 9+) for complaint and dump report data to avoid false precision.
- **Interpreting dump clusters without checking disposal site proximity.** Illegal dumping near a closed or distant disposal facility suggests an access problem (add infrastructure). Dumping in a well-served area suggests a behavioral problem (increase enforcement). Always cross-reference with facility coverage (Recipe 3).
