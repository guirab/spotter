"""Pure geometry on [lon, lat] polylines, in miles."""

from bisect import bisect_right
from math import asin, ceil, cos, radians, sin, sqrt

EARTH_RADIUS_MI = 3958.8
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
