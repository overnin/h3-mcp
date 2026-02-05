from __future__ import annotations

from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


@pytest.fixture
def cellset_cache():
    from h3_mcp.cache import CellsetCache
    from h3_mcp.runtime import get_cache, set_cache

    previous = get_cache()
    cache = CellsetCache(max_items=50, ttl_seconds=None)
    set_cache(cache)
    try:
        yield cache
    finally:
        set_cache(previous)
