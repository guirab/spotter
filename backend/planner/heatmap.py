"""Corridor lattice for the weather heatmap (PLAN.md §4.7)."""

from math import ceil, cos, floor, radians

from .geo import haversine_mi, sample_checkpoints

CORRIDOR_MI = 25
SAMPLE_EVERY_MI = 10
MAX_NODES = 400
SPACINGS_DEG = (0.25, 0.5, 1.0)  # finest first; coarser when the corridor has too many nodes
MI_PER_DEG_LAT = 69.0


def corridor_lattice(geometries):
    """(spacing_deg, [[lon, lat], …]): fixed lattice nodes within CORRIDOR_MI of any route, sorted.

    Nodes sit on multiples of the spacing, so the same place gets the same node in every plan.
    """
    samples = [(c["lon"], c["lat"]) for g in geometries for c in sample_checkpoints(g, SAMPLE_EVERY_MI)]
    for spacing in SPACINGS_DEG:
        nodes = _nodes_near(samples, spacing)
        if len(nodes) <= MAX_NODES:
            break
    return spacing, [[i * spacing, j * spacing] for i, j in sorted(nodes)]


def _nodes_near(samples, spacing):
    """Lattice indices (lon index, lat index) within CORRIDOR_MI of a sample."""
    nodes = set()
    for lon, lat in samples:
        dlat = CORRIDOR_MI / MI_PER_DEG_LAT
        dlon = dlat / max(cos(radians(abs(lat) + dlat)), 0.01)
        for i in range(ceil((lon - dlon) / spacing), floor((lon + dlon) / spacing) + 1):
            for j in range(ceil((lat - dlat) / spacing), floor((lat + dlat) / spacing) + 1):
                if (i, j) not in nodes and haversine_mi((lon, lat), (i * spacing, j * spacing)) <= CORRIDOR_MI:
                    nodes.add((i, j))
    return nodes
