"""Truck arrival time at a mile along the route (D21)."""

from bisect import bisect_right
from datetime import timedelta

METERS_PER_MILE = 1609.344


def eta_at_mile(mile, departure, instructions, total_mi, total_s):
    """`instructions` are TomTom guidance points as (offset_m, travel_time_s), ascending from (0, 0).

    Time is linear between the two instructions around the mile; with fewer than two it is
    proportional to distance over the whole route (D21 fallback).
    """
    if len(instructions) < 2:
        return departure + timedelta(seconds=total_s * mile / total_mi)
    offset = mile * METERS_PER_MILE
    offsets = [o for o, _ in instructions]
    i = min(max(bisect_right(offsets, offset) - 1, 0), len(instructions) - 2)
    (o1, t1), (o2, t2) = instructions[i], instructions[i + 1]
    f = (offset - o1) / (o2 - o1) if o2 > o1 else 0.0
    return departure + timedelta(seconds=t1 + min(max(f, 0.0), 1.0) * (t2 - t1))
