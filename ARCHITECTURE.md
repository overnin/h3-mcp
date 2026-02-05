# Architecture

## Core Pattern
The server implements stateless spatial primitives with an optional in-memory cellset cache.

- Stateless computation in tools.
- Ephemeral cache for `cellset_id` handles (TTL + LRU).
- Structured Pydantic schemas for all tool inputs and outputs.

## Layers
1. API Layer: `src/h3_mcp/server.py`
2. Tool Layer: `src/h3_mcp/tools/*.py`
3. Domain Helpers:
- `src/h3_mcp/h3_ops.py`
- `src/h3_mcp/geojson_utils.py`
- `src/h3_mcp/output_controls.py`
4. Cache Runtime:
- `src/h3_mcp/cache.py`
- `src/h3_mcp/runtime.py`
5. Schemas:
- `src/h3_mcp/models/schemas.py`
6. Resources:
- `src/h3_mcp/resources/resolution.py`

## Trade-offs
- Chosen: handle-based chaining (`cellset_id`) to reduce token pressure.
- Trade-off: ephemeral cache misses can require re-indexing.
- Chosen: composable tools over workflow endpoints for agent flexibility.
- Trade-off: orchestration complexity moves to the agent layer.

## Reliability Strategy
- Unit tests for each logical module.
- Integration tests for multi-tool scenarios.
- Performance benchmark script for large set comparisons.
