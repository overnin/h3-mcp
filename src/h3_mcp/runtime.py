from __future__ import annotations

from .cache import CellsetCache

_cache: CellsetCache = CellsetCache()


def get_cache() -> CellsetCache:
    return _cache


def set_cache(cache: CellsetCache) -> None:
    global _cache
    _cache = cache
