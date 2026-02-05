from __future__ import annotations


def resolution_guide() -> str:
    return """H3 Resolution Reference
========================
Res 0:  ~4,357,449 km²  | Continental scale
Res 1:  ~609,788 km²    | Large country
Res 2:  ~86,745 km²     | Country / large region
Res 3:  ~12,393 km²     | Region / small country
Res 4:  ~1,770 km²      | Metro area
Res 5:  ~253 km²        | City
Res 6:  ~36 km²         | District
Res 7:  ~5.16 km²       | Neighborhood
Res 8:  ~0.74 km²       | ~6 city blocks
Res 9:  ~0.105 km²      | City block
Res 10: ~0.015 km²      | Building footprint
Res 11: ~0.002 km²      | Sub-building
Res 12: ~0.0003 km²     | Parking space

Common pairings:
- Points of interest analysis: res 8-9
- Neighborhood comparison: res 6-7
- City-wide planning: res 4-5
- Regional strategy: res 2-3
- k_ring approximations: k=1 at res 9 ≈ 150m radius
"""
