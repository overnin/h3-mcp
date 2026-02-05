# H3 MCP: A Spatial Feature Store Primitive for AI Agents

## Vision

Give AI agents the ability to reason spatially by translating geography into set theory. The H3 MCP server converts coordinates into hexagonal cell grids, enabling agents to compare, aggregate, and relate heterogeneous geospatial datasets without geometry operations — using the same set logic LLMs already handle well.

**Core principle:** The LLM is a *router*, not a *relay*. Geospatial data flows tool-to-tool as structured payloads. The LLM orchestrates operations and reasons on summaries — it never interprets coordinates or cell IDs directly.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      LLM Agent                          │
│  Reasons about: counts, sets, overlaps, ratios, ranks   │
│  Never touches: raw coordinates, hex encodings          │
└────┬──────────┬──────────┬──────────┬───────────────────┘
     │          │          │          │
     ▼          ▼          ▼          ▼
┌─────────┐ ┌────────┐ ┌────────┐ ┌──────────────────────┐
│ Data     │ │ Data   │ │ Data   │ │   H3 MCP Server      │
│ Source A │ │ Src B  │ │ Src C  │ │                      │
│ (API)    │ │ (CSV)  │ │ (MCP)  │ │  • Stateless         │
│          │ │        │ │        │ │  • Pure computation   │
│ Returns  │ │Returns │ │Returns │ │  • No data storage    │
│ GeoJSON  │ │coords  │ │geojson │ │  • Spatial calculator │
└─────────┘ └────────┘ └────────┘ └──────────────────────┘
```

**What the MCP is:** A spatial calculator. Converts coordinates to hex cells, finds neighbors, changes resolution, compares cell sets, outputs GeoJSON.

**What the MCP is not:** A database, a data source, or a GIS engine. It holds no persistent state between calls. An optional ephemeral cellset cache may be used for token-light handles.

---

## Design Principles

### 1. Composable primitives over workflow endpoints

Tools should be small, single-purpose operations that agents compose into workflows the developer never anticipated. `geo_to_h3` + `k_ring` + set difference = coverage gap analysis. The same tools in different order = service area overlap detection.

**Good:** `h3_k_ring(cell_id, k)` — one operation, reusable everywhere
**Bad:** `analyze_coverage_gaps(points, radius)` — pre-baked workflow, one use case

### 2. Batch-first to prevent coordinate hallucination

LLMs will corrupt coordinates if they pass through token prediction. All tools that accept geospatial input must support **GeoJSON payloads or file references** as primary input — not individual lat/lng parameters. The agent says *"index this GeoJSON at resolution 9"*, never *"index 52.3676, 4.9041"*.

### 3. Annotated responses for LLM reasoning

Every tool response includes both:
- **Opaque payload** (cell IDs, GeoJSON) for passing to the next tool
- **Reasoning summary** (counts, areas, bounding info) for the LLM to think with

### 4. Resolution guidance as a resource, not a tool

The LLM needs to pick appropriate H3 resolutions without trial and error. A static MCP `resource` provides the reference table, so the agent can consult it before choosing parameters.

### 5. Token-light handles to prevent context overload

Most tools should accept `cellset_id` handles instead of raw `cells` arrays. Handles can be content-addressed and cached with TTL, which adds minimal state but avoids per-user sessions. Raw `cells` remain supported for small inputs and testing.

---

## Tool Inventory

### Shared Schemas & Output Controls

Most tools accept a `CellsetRef` to avoid passing large arrays through the LLM.

```
CellsetRef:
  cellset_id: string | null          # Preferred (content-addressed handle, cached with TTL)
  cells: [string] | null             # Raw cells (avoid for large inputs)
  label: string | null               # Optional label for reporting

Cell output controls (for cell arrays):
  return_mode: "summary" | "stats" | "cells"              # default "summary"
  max_cells: int | null                                   # hard cap if return_mode="cells"
  sample_cells: "first" | "random"                        # default "first"

List output controls (for row-like outputs such as aggregates, hotspots, pairs):
  return_mode: "summary" | "stats" | "items"              # default "summary"
  max_items: int | null                                   # hard cap if return_mode="items"
  sample_items: "first" | "random"                        # default "first"

GeoJSON output controls:
  return_mode: "summary" | "geojson"                      # default "geojson"
  max_features: int | null                                # hard cap for GeoJSON output

Return mode behavior:
  - "summary" returns counts/ratios only, no arrays
  - "stats" returns numeric matrices or aggregates, no arrays
  - "cells"/"items"/"geojson" return arrays subject to max_* caps
```

### Tier 1 — Core Primitives (MVP)

These are the composable building blocks. Every tool is read-only and idempotent. Tools may resolve `cellset_id` from an ephemeral cache, but no per-user sessions are required.

#### `h3_geo_to_cells`
Convert a GeoJSON FeatureCollection (points, polygons, or lines) to H3 cell sets.

```
Input:
  geojson: object          # GeoJSON FeatureCollection or single Feature
  resolution: int (0-15)   # H3 resolution level
  cache_cells: bool        # Store cellset in cache (default: true)
  return_mode: "summary" | "stats" | "cells"   # default "summary"
  max_cells: int | null
  sample_cells: "first" | "random"

Output:
  cellset_id: string | null          # Null if caching disabled
  cell_count: int
  resolution: int
  approx_cell_area: string           # e.g. "0.1 km² per cell"
  bounding_box: [minLng, minLat, maxLng, maxLat]
  cells: [                           # Only if return_mode="cells"
    {
      cell_id: string,
      source_feature_index: int,     # Which input feature produced this cell
      source_properties: object | [object]  # Carried from input GeoJSON properties (array if multiple)
    }
  ]
  summary: string                    # "342 features indexed to 298 unique cells at res 8"
```

**Design notes:**
- For points: `geo_to_h3` per point
- For polygons: `polyfill` per polygon
- For lines: `line_to_cells` per line (H3 edge traversal)
- Source properties are **carried through** so the agent can track what each cell represents
- Deduplication: if multiple features map to the same cell, all source properties are preserved as an array

**Annotations:** `readOnlyHint: true`, `idempotentHint: true`, `openWorldHint: false`

---

#### `h3_k_ring`
Find all cells within `k` hops of input cells (service areas, buffers, neighborhoods).

```
Input:
  cellset: CellsetRef
  k: int (1-50)            # Number of ring hops
  return_mode: "summary" | "stats" | "cells"   # default "summary"
  max_cells: int | null
  sample_cells: "first" | "random"

Output:
  input_cell_count: int
  ring_cell_count: int     # Total unique cells in all rings
  k: int
  approx_radius_km: float  # Approximate radius of k-ring at this resolution
  ring_cellset_id: string | null
  ring_cells: [string]     # Only if return_mode="cells"
  summary: string          # "298 input cells expanded to 4,120 ring cells (k=2, ~300m radius)"
```

**Annotations:** `readOnlyHint: true`, `idempotentHint: true`, `openWorldHint: false`

---

#### `h3_change_resolution`
Move cells up (coarser/parent) or down (finer/children) in the H3 hierarchy.

```
Input:
  cellset: CellsetRef
  target_resolution: int   # Target resolution (higher = finer)
  return_mode: "summary" | "stats" | "cells"   # default "summary"
  max_cells: int | null
  sample_cells: "first" | "random"

Output:
  input_resolution: int
  target_resolution: int
  input_cell_count: int
  output_cell_count: int
  direction: string        # "coarser" or "finer"
  cellset_id: string | null
  cells: [string]          # Only if return_mode="cells"
  summary: string          # "298 cells at res 8 → 42 cells at res 6 (neighborhood level)"
```

**Design note:** When going coarser, uses `h3_to_parent` then deduplicates. When going finer, uses `h3_to_children`. Includes compaction when going coarser to minimize cell count.

**Annotations:** `readOnlyHint: true`, `idempotentHint: true`, `openWorldHint: false`

---

#### `h3_compare_sets`
Compare two cell sets — the core "spatial join as set theory" operation.

```
Input:
  set_a: { label: string, cellset: CellsetRef }
  set_b: { label: string, cellset: CellsetRef }
  include_cells: bool      # Whether to return actual cell ID lists (default: false)

Output:
  set_a_label: string
  set_b_label: string
  set_a_count: int
  set_b_count: int
  overlap_count: int
  only_a_count: int
  only_b_count: int
  overlap_ratio_a: float   # What fraction of A overlaps with B
  overlap_ratio_b: float   # What fraction of B overlaps with A
  jaccard_index: float     # Similarity metric
  overlap_cellset_id: string | null
  only_a_cellset_id: string | null
  only_b_cellset_id: string | null
  overlap_cells: [string]  # Only if include_cells=true
  only_a_cells: [string]   # Only if include_cells=true
  only_b_cells: [string]   # Only if include_cells=true
  summary: string          # "12 of 89 transformers (13%) overlap with solar installations.
                           #  Only 8 of 340 solar cells (2%) serve stressed grid areas."
```

**This is the most important tool.** It's what turns "two unrelated datasets" into "a spatial relationship the LLM can reason about." The summary is deliberately written as a sentence the LLM can use directly in its response.

**Annotations:** `readOnlyHint: true`, `idempotentHint: true`, `openWorldHint: false`

---

#### `h3_compare_many`
Compare N cell sets in one call. This is the default for multi-dataset analysis to avoid O(N²) tool chains.

```
Input:
  sets: [{ label: string, cellset: CellsetRef }]
  matrix_metric: "jaccard" | "overlap_ratio"   # default "jaccard"
  include_cells: bool                           # Whether to return pairwise overlap cellsets (default: false)
  return_mode: "summary" | "stats"              # default "summary"
  top_k: int                                    # default 5

Output:
  set_stats: [{ label: string, cell_count: int }]
  overlap_counts: [[int]]        # Only if return_mode="stats"
  overlap_matrix: [[float]]      # Only if return_mode="stats" (directional for overlap_ratio)
  top_overlaps: [{ a: string, b: string, overlap_count: int, score: float }]  # Top K pairs by score
  overlap_cellsets: [{ a: string, b: string, cellset_id: string }]  # Only if include_cells=true (top K)
  summary: string                # "Strongest overlap: Set A vs Set C (Jaccard 0.42)"
```

**Metric note:** `overlap_ratio` is directional: overlap(A,B) / |A|.

**Annotations:** `readOnlyHint: true`, `idempotentHint: true`, `openWorldHint: false`

---

#### `h3_cells_to_geojson`
Convert cell sets back to GeoJSON for visualization.

```
Input:
  cellset: CellsetRef
  properties: object | null          # Properties to attach to each feature
  cell_properties: {cell_id: object} # Per-cell properties (optional)
  return_mode: "summary" | "geojson" # default "geojson"
  max_features: int | null

Output:
  feature_count: int
  type: "FeatureCollection"
  features: [...]                    # Standard GeoJSON, only if return_mode="geojson"
  summary: string                    # "Generated 42 hexagonal polygons at resolution 6"
```

**Annotations:** `readOnlyHint: true`, `idempotentHint: true`, `openWorldHint: false`

---

#### `h3_cell_stats`
Get metadata about cells without needing the LLM to decode H3 internals.

```
Input:
  cellset: CellsetRef

Output:
  cell_count: int
  resolution: int
  avg_area_km2: float
  total_area_km2: float
  bounding_box: [minLng, minLat, maxLng, maxLat]
  center: { lat: float, lng: float }  # Centroid of all cells
  is_contiguous: bool      # Whether cells form a connected region
  summary: string          # "89 cells at res 8, covering ~445 km² centered on Utrecht"
```

**Annotations:** `readOnlyHint: true`, `idempotentHint: true`, `openWorldHint: false`

---

### Tier 2 — Analytical Enrichment (Post-MVP)

These tools add reasoning power beyond basic primitives. They should accept `CellsetRef` plus List output controls to minimize token usage.

#### `h3_aggregate`
Roll up attributed cell data to a coarser resolution with aggregation functions.

```
Input:
  cellset: CellsetRef | null
  values_by_cell: {cell_id: {field: value}} | null
  cell_values: [{ cell_id: string, values: object }] | null
  target_resolution: int
  aggregations: { field_name: "sum" | "mean" | "max" | "min" | "count" }
  return_mode: "summary" | "stats" | "items"    # default "summary"
  max_items: int | null
  sample_items: "first" | "random"

Output:
  input_cell_count: int
  parent_cell_count: int
  parent_cellset_id: string | null
  parent_cells: [
    {
      cell_id: string,
      child_count: int,
      aggregated_values: object      # e.g. { "capacity_kw": 840, "load_pct_mean": 72.3 }
    }
  ]  # Only if return_mode="items"
  summary: string  # "298 cells at res 8 aggregated to 42 parent cells at res 6.
                   #  capacity_kw ranges from 120 to 2,400 per parent cell."
```

**Use case:** The agent indexed 340 solar panels at res 8 with `capacity_kw` per cell. Now it rolls up to res 6 to see which neighborhoods have the most capacity. This is how the agent discovers spatial patterns in attributed data.

---

#### `h3_find_hotspots`
Identify cells where a numeric attribute is significantly higher than neighbors (spatial autocorrelation).

```
Input:
  cellset: CellsetRef | null
  values_by_cell: {cell_id: value} | null
  cell_values: [{ cell_id: string, value: float }] | null
  k: int (1-5)             # Neighborhood size for comparison
  threshold: float         # Standard deviations above mean (default: 1.5)
  return_mode: "summary" | "stats" | "items"    # default "summary"
  max_items: int | null
  sample_items: "first" | "random"

Output:
  hotspot_count: int
  coldspot_count: int
  hotspot_cellset_id: string | null
  coldspot_cellset_id: string | null
  hotspots: [{ cell_id: string, value: float, z_score: float }]  # Only if return_mode="items"
  coldspots: [{ cell_id: string, value: float, z_score: float }] # Only if return_mode="items"
  summary: string  # "Found 8 hotspot cells where complaint density is >1.5σ
                   #  above the neighborhood average. Concentrated in 2 clusters."
```

---

#### `h3_distance_matrix`
Compute hop distances between two cell sets (lightweight proximity analysis).

```
Input:
  origins: { label: string, cellset: CellsetRef }
  destinations: { label: string, cellset: CellsetRef }
  max_distance: int | null  # Max hops to search (performance bound)
  return_mode: "summary" | "stats" | "items"    # default "summary"
  max_items: int | null
  sample_items: "first" | "random"

Output:
  pair_count: int
  avg_distance: float
  max_distance: int
  unreachable_count: int
  pairs: [{ origin: string, nearest_destination: string, distance_hops: int }]  # Only if return_mode="items"
  summary: string  # "Average distance from waste containers to nearest depot: 6.2 hops (~1.8 km).
                   #  14 containers have no depot within 20 hops."
```

---

#### Planned (Exploratory) Primitives

- `h3_join_by_cell` — join multiple datasets by `cell_id` and emit per-cell rollups (counts, sums, min/max), enabling attribute-aware comparisons without geometry.
- `h3_set_op` — explicit union/intersect/diff over N sets with counts and optional output cellset handles for chaining.

---

### Resource: Resolution Reference

Exposed as an MCP `resource` (not a tool) so the agent can consult it before choosing parameters.

```
URI: h3://resolution-guide

Content:
  H3 Resolution Reference
  ========================
  Res 0:  ~4,357,449 km²  | Continental scale
  Res 1:  ~609,788 km²    | Large country
  Res 2:  ~86,745 km²     | Country / large region
  Res 3:  ~12,393 km²     | Region / small country
  Res 4:  ~1,770 km²      | Metro area
  Res 5:  ~253 km²        | City
  Res 6:  ~36 km²         | District
  Res 7:  ~5.16 km²       | Neighborhood
  Res 8:  ~0.74 km²       | ~6 city blocks
  Res 9:  ~0.105 km²      | City block
  Res 10: ~0.015 km²      | Building footprint
  Res 11: ~0.002 km²      | Sub-building
  Res 12: ~0.0003 km²     | Parking space

  Common pairings:
  - Points of interest analysis: res 8-9
  - Neighborhood comparison: res 6-7
  - City-wide planning: res 4-5
  - Regional strategy: res 2-3
  - k_ring approximations: k=1 at res 9 ≈ 150m radius
```

---

## Implementation Phases

### Phase 0: Project Setup (Day 1)

**Goal:** Scaffolded Python project with FastMCP, CI, and one working tool.

- [x] Initialize repo: `h3_mcp` (Python naming convention)
- [x] Project structure:
  ```
  h3_mcp/
  ├── src/
  │   └── h3_mcp/
  │       ├── __init__.py
  │       ├── cache.py           # Cellset cache (TTL + LRU)
  │       ├── runtime.py         # Cache registry (injectable for tests)
  │       ├── h3_ops.py          # H3 wrapper utilities
  │       ├── geojson_utils.py   # GeoJSON parsing helpers
  │       ├── output_controls.py # Return_mode sampling helpers
  │       ├── server.py          # FastMCP server setup + tool registration
  │       ├── tools/
  │       │   ├── __init__.py
  │       │   ├── indexing.py    # h3_geo_to_cells
  │       │   ├── neighbors.py   # h3_k_ring
  │       │   ├── hierarchy.py   # h3_change_resolution
  │       │   ├── comparison.py  # h3_compare_sets, h3_compare_many
  │       │   ├── export.py      # h3_cells_to_geojson
  │       │   ├── stats.py       # h3_cell_stats
  │       │   └── analysis.py    # h3_aggregate, h3_find_hotspots, h3_distance_matrix
  │       ├── models/
  │       │   ├── __init__.py
  │       │   └── schemas.py     # Pydantic models for all I/O
  │       └── resources/
  │           └── resolution.py  # Resolution guide resource
  ├── tests/
  │   ├── test_indexing.py
  │   ├── test_comparison.py
  │   └── fixtures/              # Sample GeoJSON files
  │       ├── amsterdam_boundary.geojson
  │       └── sample_points.geojson
  ├── examples/
  │   ├── waste_container_analysis.md    # Scenario 1 walkthrough
  │   └── solar_grid_mismatch.md         # Scenario 2 walkthrough
  ├── pyproject.toml
  ├── README.md
  └── LICENSE
  ```
- [x] Dependencies: `h3`, `geojson`, `pydantic`, `mcp[cli]` (FastMCP)
- [x] Implement `h3_geo_to_cells` as first tool with full Pydantic schema
- [ ] Verify with MCP Inspector: `mcp dev src/h3_mcp/server.py` (blocked locally: `npx` missing)
- [x] GitHub Actions: lint (ruff), type check (mypy), test (pytest)

**Key dependency versions:**
- `h3 >= 4.0` (the v4 API uses `latlng_to_cell` not `geo_to_h3`)
- `mcp[cli]` (latest FastMCP SDK)
- Python 3.11+

---

### Phase 1: Core Primitives (Week 1)

**Goal:** All Tier 1 tools working, tested, and documented.

- [x] `h3_geo_to_cells` — with property carry-through from GeoJSON features
- [x] `h3_k_ring` — with approximate radius in summary
- [x] `h3_change_resolution` — with compaction for coarsening
- [x] `h3_compare_sets` — with labeled sets and Jaccard index
- [x] `h3_compare_many` — N-way comparison to avoid O(N²) tool chains
- [x] `h3_cells_to_geojson` — with per-cell property attachment
- [x] `h3_cell_stats` — with contiguity check and centroid
- [x] Resolution guide resource
- [x] In-memory cellset cache with TTL + LRU eviction
- [x] Unit tests for cache (order independence, TTL expiry, LRU eviction)
- [x] Unit tests for each tool (valid input, edge cases, error messages)
- [x] Integration test: full Scenario 1 flow (waste containers) as a pytest sequence

**Validation checklist per tool:**
- [x] Pydantic model for input with field descriptions
- [x] Pydantic model for output
- [x] `summary` field in every response is a natural language sentence
- [x] Annotations set (all tools are `readOnlyHint: true`)
- [x] Error messages are actionable ("Resolution must be 0-15, got 16. Use the resolution guide resource for reference.")
- [x] Output controls honored (`return_mode`, `max_cells`/`max_items`, `sample_*`)

---

## Testing Blueprint

- Each new feature must ship with unit tests in `tests/`.
- Test goals: one "happy path", one edge case, and one failure mode.
- Prefer pure, deterministic tests. Inject `time_fn` for time-based logic like cache TTL.
- Output controls must be exercised with `return_mode` to verify payload size caps.
- Definition of done: tests added, `pytest -q` passes, and failing tests demonstrate expected behavior before the fix.
- Use `tests/conftest.py` fixtures to inject shared dependencies (e.g., cache) for tool-level tests.
- Run tests inside a local virtual environment created with `python3.14 -m venv .venv`.

---

### Phase 2: Analytical Enrichment (Week 2)

**Goal:** Tier 2 tools that enable the "unexpected insight" patterns.

- [x] `h3_aggregate` — roll up with sum/mean/max/min/count
- [x] `h3_find_hotspots` — z-score based spatial outlier detection
- [x] `h3_distance_matrix` — hop distances between two cell sets
- [x] Integration test: full Scenario 2 flow (solar vs grid stress)
- [x] Performance benchmarks: test with 50K+ cell sets (target <2s response)
- [x] Add `examples/` walkthroughs with annotated tool call sequences

---

## Dev Server Integration Tests (Black-Box)

**Goal:** Validate tool behavior through a running MCP dev server (Inspector-enabled) rather than direct function calls.

### Prerequisites
- Node.js/npm installed (required by `mcp dev` to launch the Inspector).
- `.venv` created and dependencies installed.

### Tasks
- [ ] Add a pytest-driven black-box harness that starts `mcp dev src/h3_mcp/server.py` in a subprocess.
- [ ] Wait for the dev server port to open (or inspect process output) before running tests.
- [ ] Implement a client that issues MCP tool calls over stdio or Inspector endpoint (choose one, document it).
- [ ] Add teardown to terminate the dev server cleanly after tests.

### Fixture-based integration ideas
1. **Coverage flow (boundary + points)**
   - Load `tests/fixtures/amsterdam_boundary.geojson`.
   - Load `tests/fixtures/sample_points.geojson`.
   - Call `h3_geo_to_cells` for both, then `h3_k_ring`, then `h3_compare_sets`.
   - Assert `overlap_count <= set_a_count` and `overlap_ratio_a` within [0, 1].

2. **GeoJSON export round-trip**
   - Call `h3_geo_to_cells` on `sample_points.geojson` with `return_mode="summary"`.
   - Call `h3_cells_to_geojson` on the returned `cellset_id`.
   - Assert a valid FeatureCollection with closed polygon rings.

### Success criteria
- Dev server can be started and stopped from tests.
- Black-box tests run green via `pytest -q` locally.

---

### Phase 3: Hardening & Showcase (Week 3)

**Goal:** Production-quality MCP ready for listing and demo.

#### Documentation
- [x] README with:
  - Hero image (hexagonal grid visualization of a real scenario)
  - One-sentence value proposition
  - Quick start in 3 steps (install, configure, first tool call)
  - Architecture diagram showing "agent as router" pattern
  - Tool reference table with input/output summaries
  - "Why MCP, not REST?" section explaining composability
  - "Coordinate hallucination prevention" section (the batch-first pattern)
- [x] `ARCHITECTURE.md` — design decisions and trade-offs
- [x] `AGENTS.md` — guide for LLM agent developers on how to compose tools effectively

#### Distribution
- [ ] PyPI package: `pip install h3-mcp`
- [ ] Smithery listing (MCP registry)
- [ ] Submit PR to `punkpeye/awesome-mcp-servers`
- [ ] Submit PR to `modelcontextprotocol/servers` (official MCP servers list)

#### Showcase
- [ ] Interactive demo: Jupyter notebook with real Amsterdam data
  - Uses Amsterdam Open Data API for waste containers
  - Runs H3 MCP tools in sequence
  - Renders results in Kepler.gl or Folium
  - Shows the "unexpected insight" (overflow vs gap) emerging step by step
- [ ] GIF recording of an agent session using the MCP (for README hero image)
- [ ] Blog post / dev.to article: "Building an MCP that gives AI agents spatial reasoning"

---

### Phase 4: Evaluations (Week 3-4)

**Goal:** Prove the MCP works with real LLM agents via structured evaluation.

Following MCP Builder evaluation guidelines:

- [ ] Create 10 evaluation questions requiring multi-tool composition
- [ ] Each question must require 3+ tool calls to answer
- [ ] Verify answers manually
- [ ] Output as `evaluations.xml`

**Sample evaluation questions:**

1. "Given the Amsterdam municipal boundary and 5,200 waste container locations, what percentage of the city (by area) is more than 200m from any container?" *(requires: geo_to_cells, k_ring, compare_sets)*

2. "Index these 89 transformer locations and 340 solar panel locations. At neighborhood level (res 7), which neighborhoods have transformers above 80% load but zero solar capacity?" *(requires: geo_to_cells ×2, change_resolution ×2, compare_sets)*

3. "Find spatial hotspots where waste complaint density exceeds 1.5 standard deviations above the local average. How many of these hotspots are within the service area of an existing container?" *(requires: geo_to_cells, find_hotspots, k_ring, compare_sets)*

---

## Key Technical Decisions

### Why Python over TypeScript

- `h3-py` is the most mature H3 binding (direct C library wrapper)
- GIS ecosystem is Python-native (GeoPandas, Shapely, Fiona)
- FastMCP Python SDK is first-class
- Target users (GIS engineers, data scientists) prefer Python

### Why no sessions (minimal state)

- No session management complexity
- Horizontally scalable with an optional ephemeral cache
- No data ownership / privacy concerns (no persistent storage)
- Agent manages its own state between calls, or replays inputs if cache misses

### Why batch GeoJSON input (not individual lat/lng)

- Prevents coordinate hallucination (data flows tool-to-tool, not through LLM token prediction)
- Preserves source properties (feature attributes carry through to cells)
- Performance: one tool call for 5,000 points, not 5,000 calls
- Matches how real geospatial data is exchanged

### Why annotated summaries in every response

- LLMs reason on natural language, not data structures
- Summary field is the "interface" the LLM reads
- Cell ID arrays are the "interface" the next tool reads
- Same response serves two consumers (LLM brain + tool pipeline)

### H3 v4 API alignment

H3 v4 renamed most functions. The MCP tool names should align with MCP conventions (snake_case with prefix), not H3's internal naming:

| H3 v4 function | MCP tool |
|----------------|----------|
| `latlng_to_cell` | `h3_geo_to_cells` (batch) |
| `grid_disk` | `h3_k_ring` |
| `cell_to_parent` | `h3_change_resolution` |
| `cell_to_children` | `h3_change_resolution` |
| `cells_to_geo` | `h3_cells_to_geojson` |

---

## Success Metrics

### Adoption
- Listed in awesome-mcp-servers within 1 month
- 100+ GitHub stars within 3 months
- 500+ PyPI downloads/month within 3 months

### Quality
- All 10 evaluation questions answered correctly by Claude/GPT-4
- <2s response time for 50K cell operations
- Zero coordinate hallucination in agent test scenarios

### Portfolio impact
- Demonstrates: MCP protocol expertise, GIS domain knowledge, product thinking, API design taste
- Cited in at least one "best MCP servers" roundup or blog post
