from __future__ import annotations

from h3_mcp.resources.resolution import resolution_guide


def test_resolution_guide_contains_expected_rows() -> None:
    text = resolution_guide()
    assert "Res 0" in text
    assert "Res 9" in text
    assert "Common pairings" in text
