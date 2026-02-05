from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from hashlib import sha256
from typing import Callable, Iterable
import time


def normalize_cells(cells: Iterable[str]) -> list[str]:
    return sorted(set(cells))


def make_cellset_id(cells: Iterable[str]) -> str:
    normalized = normalize_cells(cells)
    digest = sha256("\n".join(normalized).encode("utf-8")).hexdigest()
    return f"cellset_{digest}"


@dataclass(frozen=True)
class CacheEntry:
    cells: tuple[str, ...]
    created_at: float
    expires_at: float


class CellsetCache:
    def __init__(
        self,
        max_items: int = 1024,
        ttl_seconds: int | None = 3600,
        time_fn: Callable[[], float] | None = None,
    ) -> None:
        if max_items < 1:
            raise ValueError("max_items must be >= 1.")
        if ttl_seconds is not None and ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be > 0 when set.")
        self._max_items = max_items
        self._ttl_seconds = ttl_seconds
        self._time_fn = time_fn or time.time
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()

    def __len__(self) -> int:
        self._purge_expired(self._time_fn())
        return len(self._store)

    def _expires_at(self, now: float) -> float:
        if self._ttl_seconds is None:
            return float("inf")
        return now + self._ttl_seconds

    def _purge_expired(self, now: float) -> None:
        expired_keys = [
            key for key, entry in self._store.items() if entry.expires_at <= now
        ]
        for key in expired_keys:
            self._store.pop(key, None)

    def _enforce_limits(self) -> None:
        while len(self._store) > self._max_items:
            self._store.popitem(last=False)

    def prune(self) -> None:
        now = self._time_fn()
        self._purge_expired(now)
        self._enforce_limits()

    def put_cells(self, cells: Iterable[str]) -> str:
        normalized = normalize_cells(cells)
        cellset_id = make_cellset_id(normalized)
        now = self._time_fn()
        entry = CacheEntry(
            cells=tuple(normalized),
            created_at=now,
            expires_at=self._expires_at(now),
        )
        self._store[cellset_id] = entry
        self._store.move_to_end(cellset_id)
        self._enforce_limits()
        return cellset_id

    def get_cells(self, cellset_id: str) -> list[str] | None:
        now = self._time_fn()
        entry = self._store.get(cellset_id)
        if not entry:
            return None
        if entry.expires_at <= now:
            self._store.pop(cellset_id, None)
            return None
        self._store.move_to_end(cellset_id)
        return list(entry.cells)
