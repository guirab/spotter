"""Orchestration of a plan request: routing, checkpoints with ETAs, weather risk, then ranking."""

from django.conf import settings

from . import openmeteo, tomtom
from .eta import eta_at_mile
from .geo import sample_checkpoints
from .ranking import rank_routes
from .risk import classify

KG_PER_LB = 0.45359237


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
    return rank_routes(routes)


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
