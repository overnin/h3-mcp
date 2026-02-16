# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

H3 MCP is a Python MCP (Model Context Protocol) server that gives AI agents spatial reasoning by converting geospatial geometry into composable H3 hexagonal set operations. It exposes 10 stateless, read-only, idempotent tools and 1 resource via FastMCP.

## Commands

```bash
# Setup
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# Run dev server
mcp dev src/h3_mcp/server.py

# Tests
pytest -q                          # all tests
pytest tests/test_indexing.py      # single file
pytest tests/test_indexing.py::test_name -v  # single test

# Lint & type check (CI runs these)
ruff check src tests
mypy src
```

## Architecture

```
GeoJSON/coords → Tool Layer → summaries + cellset handles → LLM reasoning
```

**Layers (top to bottom):**

1. **API Layer** — `src/h3_mcp/server.py`: FastMCP instance, registers all tools with `ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)`.

2. **Tool Layer** — `src/h3_mcp/tools/*.py`: Each file is one or more tools. Tools accept/return Pydantic models from `models/schemas.py`. Tools use `cellset_id` handles to chain results without passing raw cell arrays.

3. **Domain Helpers**:
   - `h3_ops.py` — Thin wrappers around the `h3` library (cell conversions, boundaries, compaction).
   - `geojson_utils.py` — GeoJSON parsing (`iter_features`, `bounding_box_from_geojson`).
   - `output_controls.py` — Sampling and truncation logic (`apply_sampling`, `apply_cell_controls`).

4. **Cache Runtime** — `cache.py` + `runtime.py`: Content-addressed LRU+TTL `CellsetCache` singleton. Tools store cell sets and return opaque `cellset_id` handles; downstream tools resolve handles via `resolve_cellset()`.

5. **Schemas** — `models/schemas.py`: ~25 Pydantic models with strict validation (`StrictModel` forbids extra fields). Key type aliases: `Resolution` (0–15), `KRing` (1–50), `AggregationOp`.

6. **Resources** — `resources/resolution.py`: Static H3 resolution reference table.

## Key Design Decisions

- **Cellset handles over raw arrays**: Tools return `cellset_id` strings. Downstream tools accept these handles to avoid large token payloads. If a handle expires (cache eviction), re-run indexing.
- **Composable primitives, not workflow endpoints**: The agent chains tools differently per question. No fixed pipelines.
- **Batch GeoJSON ingestion**: Use `h3_geo_to_cells` with GeoJSON instead of single lat/lng to prevent coordinate hallucination.
- **Output controls**: All tools default to `return_mode="summary"`. Use `max_cells`, `max_items`, `max_features`, `top_k` to cap payloads.

## Testing

- Tests live in `tests/` and use pytest. The `cellset_cache` fixture (in `conftest.py`) isolates cache state per test.
- Test fixtures: `tests/fixtures/amsterdam_boundary.geojson`, `tests/fixtures/sample_points.geojson`.
- Integration tests (`test_integration_scenario*.py`) exercise multi-tool chains.
- `test_dev_server_blackbox.py` tests the MCP protocol via async client.
- **All tests must pass inside `docker compose run --rm h3-mcp pytest -q`.** Never hardcode local paths like `.venv/bin/` — use `shutil.which()` or `PATH`-based resolution so tests work in both local venvs and Docker containers. This is required for CI/CD portability.

## Code Style

- Python >=3.11, ruff line-length 100, E501 ignored.
- All tool I/O uses Pydantic models defined in `models/schemas.py`.
- `from __future__ import annotations` used throughout.
