from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Iterable, TypeVar, Literal

T = TypeVar("T")


@dataclass(frozen=True)
class SampleConfig:
    max_items: int | None
    sample: Literal["first", "random"]


def _apply_sampling(items: list[T], config: SampleConfig, rng: random.Random) -> list[T]:
    if config.max_items is None or len(items) <= config.max_items:
        return items
    if config.sample == "random":
        return rng.sample(items, config.max_items)
    return items[: config.max_items]


def apply_sampling(
    items: Iterable[T],
    max_items: int | None,
    sample: Literal["first", "random"],
    rng: random.Random | None = None,
) -> list[T]:
    rng = rng or random.Random(0)
    item_list = list(items)
    return _apply_sampling(item_list, SampleConfig(max_items, sample), rng)


def apply_list_controls(
    items: Iterable[T],
    return_mode: Literal["summary", "stats", "items"],
    max_items: int | None,
    sample: Literal["first", "random"],
    rng: random.Random | None = None,
) -> list[T] | None:
    if return_mode != "items":
        return None
    rng = rng or random.Random(0)
    item_list = list(items)
    return _apply_sampling(item_list, SampleConfig(max_items, sample), rng)


def apply_cell_controls(
    cells: Iterable[str],
    return_mode: Literal["summary", "stats", "cells"],
    max_cells: int | None,
    sample: Literal["first", "random"],
    rng: random.Random | None = None,
) -> list[str] | None:
    if return_mode != "cells":
        return None
    rng = rng or random.Random(0)
    cell_list = list(cells)
    return _apply_sampling(cell_list, SampleConfig(max_cells, sample), rng)
