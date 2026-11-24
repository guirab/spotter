"""Orchestration of a plan request: routing, checkpoints with ETAs, weather risk, then ranking."""

from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.core.cache import cache

from . import openmeteo, tomtom
from .eta import eta_at_mile
from .geo import overlap_ratio, sample_checkpoints, via_points
from .heatmap import corridor_lattice
from .ranking import rank_routes
from .risk import classify

KG_PER_LB = 0.45359237
PLAN_TTL_S = 60 * 60
HEATMAP_HOURS = 49  # 0–48 h after departure (D13)
ROUTES_WANTED = 3
VIA_OFFSET = 0.15  # of the straight-line distance (D20)
DUPLICATE_OVERLAP = 0.9  # share of one route within 0.5 mi of another (D20)


def build_plan(origin, destination, departure_at, load_lb, interval_mi):
    """The API response body. Raises tomtom.NoRouteError and tomtom/openmeteo.UpstreamError."""
    gross_kg = round((load_lb + settings.TRUCK_TARE_LB) * KG_PER_LB)  # PLAN.md A1
    routes = _distinct(tomtom.calculate_routes(origin, destination, departure_at, gross_kg))
    if len(routes) < ROUTES_WANTED:
        routes = _distinct(routes + _via_routes(origin, destination, departure_at, gross_kg, routes[0]))
    routes = routes[:ROUTES_WANTED]
    warnings = [] if len(routes) == ROUTES_WANTED else [
        f"Only {len(routes)} distinct route{'s' if len(routes) > 1 else ''} found."
    ]
    for route_id, route in zip("ABC", routes):
        route["id"] = route_id
        route["checkpoints"] = _checkpoints(route, departure_at, interval_mi)
    checkpoints = [c for route in routes for c in route["checkpoints"]]
    # One batch for every route, so points shared between routes are fetched once.
    forecasts = openmeteo.get_hourly(openmeteo.snap(c["lat"], c["lon"]) for c in checkpoints)
    for c in checkpoints:
        c["weather"] = openmeteo.weather_at(forecasts[openmeteo.snap(c["lat"], c["lon"])], c["eta"])
        c.update(classify(c["weather"], load_lb))
    plan_id = uuid4().hex
    # Shared cache, so whichever worker serves /api/heatmap finds it (PLAN.md §5.2).
    cache.set(
        f"plan:{plan_id}",
        {"geometries": [r["geometry"] for r in routes], "departure_at": departure_at, "load_lb": load_lb},
        PLAN_TTL_S,
    )
    ranked = rank_routes(routes)
    return {"plan_id": plan_id, **ranked, "warnings": warnings + ranked["warnings"]}


def build_heatmap(plan_id):
    """Hourly load-aware risk scores on the corridor lattice, or None when the plan expired.

    Raises openmeteo.UpstreamError.
    """
    plan = cache.get(f"plan:{plan_id}")
    if plan is None:
        return None
    spacing, nodes = corridor_lattice(plan["geometries"])
    forecasts = openmeteo.get_hourly(openmeteo.snap(lat, lon) for lon, lat in nodes)
    start = plan["departure_at"].replace(minute=0, second=0, microsecond=0)
    hours = [start + timedelta(hours=h) for h in range(HEATMAP_HOURS)]
    scores = []
    for lon, lat in nodes:
        forecast = forecasts[openmeteo.snap(lat, lon)]
        scores.append([classify(openmeteo.weather_at(forecast, at), plan["load_lb"])["score"] for at in hours])
    return {"start_at": start, "spacing_deg": spacing, "points": nodes, "scores": scores}


def _via_routes(origin, destination, departure_at, gross_kg, primary):
    """Best effort (D20): the route through a point either side of the primary one, skipping calls that fail."""
    start, end = [origin["lon"], origin["lat"]], [destination["lon"], destination["lat"]]
    routes = []
    for lon, lat in via_points(primary["geometry"], start, end, VIA_OFFSET):
        try:
            routes += tomtom.calculate_routes(origin, destination, departure_at, gross_kg, via={"lat": lat, "lon": lon})
        except (tomtom.NoRouteError, tomtom.UpstreamError):
            pass  # e.g. a via-point with no road near it; the warning covers a missing route
    return routes


def _distinct(routes):
    """Routes in order, dropping each one that duplicates a route kept before it (D20).

    Either way round: a route lying almost entirely along a longer one duplicates it too.
    """
    kept = []
    for route in routes:
        a = route["geometry"]
        overlaps = (max(overlap_ratio(a, k["geometry"]), overlap_ratio(k["geometry"], a)) for k in kept)
        if all(overlap <= DUPLICATE_OVERLAP for overlap in overlaps):
            kept.append(route)
    return kept


def _checkpoints(route, departure_at, interval_mi):
    instructions = route.pop("instructions")
    return [
        {
            "mile": round(c["mile"], 1),
            "lat": round(c["lat"], 5),
            "lon": round(c["lon"], 5),
            "segment_mi": round(c["segment_mi"], 2),
            "eta": eta_at_mile(
                c["mile"], departure_at, instructions, route["distance_mi"], route["duration_s"]
            ).replace(microsecond=0),
        }
        for c in sample_checkpoints(route["geometry"], interval_mi, route["distance_mi"])
    ]
