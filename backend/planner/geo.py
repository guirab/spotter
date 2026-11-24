"""Pure geometry on [lon, lat] polylines, in miles."""

from bisect import bisect_right
from math import asin, ceil, cos, floor, hypot, pi, radians, sin, sqrt

EARTH_RADIUS_MI = 3958.8
MI_PER_DEG = EARTH_RADIUS_MI * pi / 180
SAME_SPOT_MI = 0.01


def haversine_mi(a, b):
    lon1, lat1, lon2, lat2 = map(radians, (*a, *b))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_MI * asin(sqrt(h))


def cumulative_miles(points):
    total, cum = 0.0, [0.0]
    for a, b in zip(points, points[1:]):
        total += haversine_mi(a, b)
        cum.append(total)
    return cum


def point_at_mile(points, cum, mile):
    """[lon, lat] at `mile` along the line, linear inside the segment (fine at checkpoint spacing)."""
    i = min(max(bisect_right(cum, mile) - 1, 0), len(points) - 2)
    span = cum[i + 1] - cum[i]
    f = (mile - cum[i]) / span if span else 0.0
    (lon1, lat1), (lon2, lat2) = points[i], points[i + 1]
    return [lon1 + f * (lon2 - lon1), lat1 + f * (lat2 - lat1)]


def sample_checkpoints(points, interval_mi, length_mi=None):
    """Checkpoints at mile 0, every `interval_mi`, and the destination (D22).

    Each one covers half the gap to its neighbours on both sides, so the segments sum to the length (D8).
    `length_mi` (the router's distance) rescales the line's own length, so miles and ETAs agree with it.
    """
    cum = cumulative_miles(points)
    if length_mi and cum[-1]:
        cum = [c * length_mi / cum[-1] for c in cum]
    total = cum[-1]
    # A multiple within ~50 ft of the end is the destination itself, not a separate checkpoint.
    inner = [m for m in range(interval_mi, ceil(total), interval_mi) if m < total - SAME_SPOT_MI]
    miles = [0, *inner, total]
    edges = [0.0, *((a + b) / 2 for a, b in zip(miles, miles[1:])), total]
    checkpoints = []
    for mile, start, end in zip(miles, edges, edges[1:]):
        lon, lat = point_at_mile(points, cum, mile)
        checkpoints.append({"mile": mile, "lat": lat, "lon": lon, "segment_mi": end - start})
    return checkpoints


def overlap_ratio(a, b, near_mi=0.5):
    """Share of line A's 1 mi samples within `near_mi` of line B, for the route dedupe (D20)."""
    # Cells at least `near_mi` wide on both axes, so a near point is always in one of the 9 cells around a sample.
    cell = near_mi / (MI_PER_DEG * cos(radians(max(abs(lat) for _, lat in (*a, *b)))))
    grid = {}
    # B densified to near_mi / 2, so its samples stand in for the line itself to within ~0.13 mi.
    for p, q in zip(b, b[1:]):
        n = max(ceil(haversine_mi(p, q) / (near_mi / 2)), 1)
        for k in range(n + 1):
            point = [p[0] + (q[0] - p[0]) * k / n, p[1] + (q[1] - p[1]) * k / n]
            grid.setdefault((floor(point[0] / cell), floor(point[1] / cell)), []).append(point)
    samples = [[c["lon"], c["lat"]] for c in sample_checkpoints(a, 1)]
    near = sum(
        any(
            haversine_mi(s, q) <= near_mi
            for i in (-1, 0, 1)
            for j in (-1, 0, 1)
            for q in grid.get((floor(s[0] / cell) + i, floor(s[1] / cell) + j), ())
        )
        for s in samples
    )
    return near / len(samples)


def via_points(line, start, end, fraction):
    """Two points either side of the line's midpoint, `fraction` of the start–end straight line away from it.

    They lie perpendicular to that straight line (D20). An empty list when start and end coincide.
    """
    cum = cumulative_miles(line)
    lon, lat = point_at_mile(line, cum, cum[-1] / 2)
    k = cos(radians(lat))  # degrees of longitude to local degrees east
    east, north = (end[0] - start[0]) * k, end[1] - start[1]
    if not (norm := hypot(east, north)):
        return []
    offset = fraction * haversine_mi(start, end) / MI_PER_DEG / norm
    return [[lon - north * offset / k, lat + east * offset], [lon + north * offset / k, lat - east * offset]]
