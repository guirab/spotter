"""Orchestration of a plan request: routing, checkpoints with ETAs, weather risk, then ranking."""

from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.core.cache import cache

from . import openmeteo, tomtom
from .eta import eta_at_mile
from .geo import sample_checkpoints
from .heatmap import corridor_lattice
from .ranking import rank_routes
from .risk import classify

KG_PER_LB = 0.45359237
PLAN_TTL_S = 60 * 60
HEATMAP_HOURS = 49  # 0–48 h after departure (D13)


def build_plan(origin, destination, departure_at, load_lb, interval_mi):
    """The API response body. Raises tomtom.NoRouteError and tomtom/openmeteo.UpstreamError."""
    gross_kg = round((load_lb + settings.TRUCK_TARE_LB) * KG_PER_LB)  # PLAN.md A1
    routes = tomtom.calculate_routes(origin, destination, departure_at, gross_kg)
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
    return {"plan_id": plan_id, **rank_routes(routes)}


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
