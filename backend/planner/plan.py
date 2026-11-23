"""Orchestration of a plan request: routing, then checkpoints with ETAs."""

from django.conf import settings

from . import tomtom
from .eta import eta_at_mile
from .geo import sample_checkpoints

KG_PER_LB = 0.45359237


def build_plan(origin, destination, departure_at, load_lb, interval_mi):
    """The API response body. Raises tomtom.NoRouteError / tomtom.UpstreamError."""
    gross_kg = round((load_lb + settings.TRUCK_TARE_LB) * KG_PER_LB)  # PLAN.md A1
    route = tomtom.calculate_route(origin, destination, departure_at, gross_kg)
    instructions = route.pop("instructions")
    route["checkpoints"] = [
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
    return {"routes": [{"id": "A", **route}]}
