from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Literal

from dotenv import load_dotenv
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp import types
from pydantic import AnyHttpUrl

if __package__ in (None, ""):
    project_src = Path(__file__).resolve().parents[1]
    if str(project_src) not in sys.path:
        sys.path.insert(0, str(project_src))

from h3_mcp.resources.resolution import resolution_guide
from h3_mcp.tools.analysis import h3_aggregate, h3_distance_matrix, h3_find_hotspots
from h3_mcp.tools.comparison import h3_compare_many, h3_compare_sets
from h3_mcp.tools.components import h3_connected_components
from h3_mcp.tools.export import h3_cells_to_geojson
from h3_mcp.tools.hierarchy import h3_change_resolution
from h3_mcp.tools.indexing import h3_geo_to_cells
from h3_mcp.tools.neighbors import h3_k_ring
from h3_mcp.tools.stats import h3_cell_stats

load_dotenv()

_TRANSPORTS = {"stdio", "sse", "streamable-http"}
_raw_transport = os.environ.get("H3_MCP_TRANSPORT", "streamable-http")
if _raw_transport not in _TRANSPORTS:
    raise ValueError(f"H3_MCP_TRANSPORT must be one of {_TRANSPORTS}, got {_raw_transport!r}")
transport: Literal["stdio", "sse", "streamable-http"] = _raw_transport  # type: ignore[assignment]
host = os.environ.get("H3_MCP_HOST", "127.0.0.1")
port = int(os.environ.get("H3_MCP_PORT", "8000"))
api_key = os.environ.get("H3_MCP_API_KEY", "")


class ApiKeyVerifier:
    """Verify bearer tokens against a static API key."""

    def __init__(self, key: str) -> None:
        self._key = key

    async def verify_token(self, token: str) -> AccessToken | None:
        if token != self._key:
            raise ValueError("Invalid API key")
        return AccessToken(
            token=token,
            client_id="api-key-client",
            scopes=[],
            expires_at=None,
        )


auth_settings: AuthSettings | None = None
token_verifier: ApiKeyVerifier | None = None
if api_key:
    auth_settings = AuthSettings(
        issuer_url=AnyHttpUrl(f"http://{host}:{port}"),
        resource_server_url=AnyHttpUrl(f"http://{host}:{port}"),
    )
    token_verifier = ApiKeyVerifier(api_key)

mcp = FastMCP(
    "h3-mcp",
    host=host,
    port=port,
    auth=auth_settings,
    token_verifier=token_verifier,
)


def register_tools(server: FastMCP) -> None:
    server.tool(
        name="h3_geo_to_cells",
        description="Convert GeoJSON features to H3 cell sets.",
        annotations=types.ToolAnnotations(
            readOnlyHint=True, idempotentHint=True, openWorldHint=False
        ),
    )(h3_geo_to_cells)
    server.tool(
        name="h3_k_ring",
        description="Expand cell sets by k-ring hops.",
        annotations=types.ToolAnnotations(
            readOnlyHint=True, idempotentHint=True, openWorldHint=False
        ),
    )(h3_k_ring)
    server.tool(
        name="h3_change_resolution",
        description="Change H3 resolution of a cell set.",
        annotations=types.ToolAnnotations(
            readOnlyHint=True, idempotentHint=True, openWorldHint=False
        ),
    )(h3_change_resolution)
    server.tool(
        name="h3_compare_sets",
        description="Compare two cell sets and compute overlaps.",
        annotations=types.ToolAnnotations(
            readOnlyHint=True, idempotentHint=True, openWorldHint=False
        ),
    )(h3_compare_sets)
    server.tool(
        name="h3_compare_many",
        description="Compare N cell sets and compute top overlaps.",
        annotations=types.ToolAnnotations(
            readOnlyHint=True, idempotentHint=True, openWorldHint=False
        ),
    )(h3_compare_many)
    server.tool(
        name="h3_cells_to_geojson",
        description="Convert H3 cell sets to GeoJSON polygons.",
        annotations=types.ToolAnnotations(
            readOnlyHint=True, idempotentHint=True, openWorldHint=False
        ),
    )(h3_cells_to_geojson)
    server.tool(
        name="h3_cell_stats",
        description="Compute metadata about H3 cell sets.",
        annotations=types.ToolAnnotations(
            readOnlyHint=True, idempotentHint=True, openWorldHint=False
        ),
    )(h3_cell_stats)
    server.tool(
        name="h3_aggregate",
        description="Aggregate numeric values over coarser H3 parents.",
        annotations=types.ToolAnnotations(
            readOnlyHint=True, idempotentHint=True, openWorldHint=False
        ),
    )(h3_aggregate)
    server.tool(
        name="h3_find_hotspots",
        description="Detect hotspot and coldspot cells by neighborhood z-score.",
        annotations=types.ToolAnnotations(
            readOnlyHint=True, idempotentHint=True, openWorldHint=False
        ),
    )(h3_find_hotspots)
    server.tool(
        name="h3_distance_matrix",
        description="Compute hop distances between two H3 cell sets.",
        annotations=types.ToolAnnotations(
            readOnlyHint=True, idempotentHint=True, openWorldHint=False
        ),
    )(h3_distance_matrix)

    server.tool(
        name="h3_connected_components",
        description="Split a cellset into contiguous connected components.",
        annotations=types.ToolAnnotations(
            readOnlyHint=True, idempotentHint=True, openWorldHint=False
        ),
    )(h3_connected_components)

    server.resource(
        "h3://resolution-guide",
        name="resolution-guide",
        description="Reference table for H3 resolutions and typical use cases.",
        mime_type="text/plain",
    )(resolution_guide)


register_tools(mcp)

if __name__ == "__main__":
    mcp.run(transport=transport)
