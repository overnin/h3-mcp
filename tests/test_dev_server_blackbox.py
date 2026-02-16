from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_fixture(name: str) -> dict:
    fixture_path = _PROJECT_ROOT / "tests" / "fixtures" / name
    return json.loads(fixture_path.read_text())


def _require_structured(result):
    assert result.isError is False
    assert result.structuredContent is not None
    return result.structuredContent


def _server_params() -> StdioServerParameters:
    mcp_bin = shutil.which("mcp")
    assert mcp_bin is not None, "mcp CLI not found on PATH; activate your venv or install mcp[cli]"
    return StdioServerParameters(
        command=mcp_bin,
        args=["run", "src/h3_mcp/server.py:mcp", "--transport", "stdio"],
        cwd=str(_PROJECT_ROOT),
    )


@pytest.mark.anyio
async def test_dev_server_coverage_flow():
    boundary_geojson = _load_fixture("amsterdam_boundary.geojson")
    points_geojson = _load_fixture("sample_points.geojson")

    server_params = _server_params()

    async with stdio_client(server_params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()

            boundary = await session.call_tool(
                "h3_geo_to_cells",
                {"payload": {"geojson": boundary_geojson, "resolution": 9}},
            )
            boundary_payload = _require_structured(boundary)
            boundary_id = boundary_payload["cellset_id"]
            assert boundary_id

            points = await session.call_tool(
                "h3_geo_to_cells",
                {"payload": {"geojson": points_geojson, "resolution": 9}},
            )
            points_payload = _require_structured(points)
            points_id = points_payload["cellset_id"]
            assert points_id

            ring = await session.call_tool(
                "h3_k_ring",
                {"payload": {"cellset": {"cellset_id": points_id}, "k": 1}},
            )
            ring_payload = _require_structured(ring)
            ring_id = ring_payload["ring_cellset_id"]
            assert ring_id

            compare = await session.call_tool(
                "h3_compare_sets",
                {
                    "payload": {
                        "set_a": {"label": "city", "cellset": {"cellset_id": boundary_id}},
                        "set_b": {"label": "coverage", "cellset": {"cellset_id": ring_id}},
                        "include_cells": False,
                    }
                },
            )
            compare_payload = _require_structured(compare)
            assert compare_payload["overlap_count"] <= compare_payload["set_a_count"]
            assert 0.0 <= compare_payload["overlap_ratio_a"] <= 1.0


@pytest.mark.anyio
async def test_dev_server_geojson_roundtrip():
    points_geojson = _load_fixture("sample_points.geojson")

    server_params = _server_params()

    async with stdio_client(server_params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()

            points = await session.call_tool(
                "h3_geo_to_cells",
                {"payload": {"geojson": points_geojson, "resolution": 9}},
            )
            points_payload = _require_structured(points)
            points_id = points_payload["cellset_id"]
            assert points_id

            geojson_result = await session.call_tool(
                "h3_cells_to_geojson",
                {"payload": {"cellset": {"cellset_id": points_id}}},
            )
            geojson_payload = _require_structured(geojson_result)
            assert geojson_payload["type"] == "FeatureCollection"
            features = geojson_payload["features"]
            assert isinstance(features, list)
            assert features
            coords = features[0]["geometry"]["coordinates"][0]
            assert coords[0] == coords[-1]
