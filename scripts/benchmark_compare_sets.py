from __future__ import annotations

from pathlib import Path
import sys

import h3

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from h3_mcp.benchmarks import benchmark_compare_sets, generate_disk_cells


def main() -> None:
    center = h3.latlng_to_cell(37.775, -122.418, 9)
    k = 130  # ~51k cells
    cells = generate_disk_cells(center, k)
    elapsed = benchmark_compare_sets(cells, cells)
    print(f"compare_sets on {len(cells)} cells: {elapsed:.3f}s")


if __name__ == "__main__":
    main()
