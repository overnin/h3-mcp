from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def test_server_module_can_load_from_file_path() -> None:
    server_path = Path(__file__).resolve().parents[1] / "src" / "h3_mcp" / "server.py"
    spec = spec_from_file_location("h3_server_module", server_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    assert getattr(module, "mcp", None) is not None
