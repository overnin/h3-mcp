from __future__ import annotations

from h3_mcp.cache import CellsetCache


def test_cellset_id_is_order_independent() -> None:
    cache = CellsetCache(max_items=10, ttl_seconds=None)
    first_id = cache.put_cells(["b", "a", "a"])
    second_id = cache.put_cells(["a", "b"])
    assert first_id == second_id
    assert cache.get_cells(first_id) == ["a", "b"]


def test_cache_ttl_expiration() -> None:
    now = [1000.0]

    def time_fn() -> float:
        return now[0]

    cache = CellsetCache(max_items=10, ttl_seconds=10, time_fn=time_fn)
    cellset_id = cache.put_cells(["a"])
    assert cache.get_cells(cellset_id) == ["a"]
    now[0] = 1011.0
    assert cache.get_cells(cellset_id) is None
    assert len(cache) == 0


def test_cache_lru_eviction() -> None:
    cache = CellsetCache(max_items=2, ttl_seconds=None)
    id_a = cache.put_cells(["a"])
    id_b = cache.put_cells(["b"])
    assert cache.get_cells(id_a) == ["a"]
    id_c = cache.put_cells(["c"])
    assert cache.get_cells(id_b) is None
    assert cache.get_cells(id_a) == ["a"]
    assert cache.get_cells(id_c) == ["c"]


def test_cache_returns_copy() -> None:
    cache = CellsetCache(max_items=5, ttl_seconds=None)
    cellset_id = cache.put_cells(["a", "b"])
    cells = cache.get_cells(cellset_id)
    assert cells == ["a", "b"]
    assert cells is not None
    cells.append("c")
    assert cache.get_cells(cellset_id) == ["a", "b"]
