from datetime import UTC, datetime, timedelta
from urllib.parse import quote

import requests
from django.conf import settings

from .eta import METERS_PER_MILE

BASE_URL = "https://api.tomtom.com"
TIMEOUT = (5, 20)
# A departure this close is sent as "now": a timestamp could be in the past when TomTom receives it.
DEPART_NOW_MARGIN = timedelta(minutes=1)


class UpstreamError(Exception):
    """TomTom failed or could not be reached."""


class NoRouteError(Exception):
    """TomTom found no route between the points."""


def _get(path, params):
    try:
        response = requests.get(
            f"{BASE_URL}{path}", params={**params, "key": settings.TOMTOM_API_KEY}, timeout=TIMEOUT
        )
    except requests.RequestException as exc:
        # The exception text carries the request URL, and with it the API key.
        raise UpstreamError(type(exc).__name__) from None
    if response.status_code == 400 and "NO_ROUTE_FOUND" in response.text:
        raise NoRouteError()
    if not response.ok:
        raise UpstreamError(f"TomTom returned HTTP {response.status_code}")
    return response.json()


def geocode(query):
    """Up to 5 US places as [{label, lat, lon}]."""
    data = _get(
        f"/search/2/search/{quote(query, safe='')}.json",
        {"typeahead": "true", "limit": 5, "countrySet": "US", "idxSet": "Geo,PAD,Addr"},
    )
    return [
        {"label": r["address"]["freeformAddress"], "lat": r["position"]["lat"], "lon": r["position"]["lon"]}
        for r in data["results"]
    ]


def calculate_routes(origin, destination, departure_at, gross_kg):
    """Up to 3 truck routes, primary first, each {distance_mi, duration_s, geometry: [[lon, lat], ...], instructions}.

    `instructions` are the guidance points as (offset_m, travel_time_s), for checkpoint ETAs.
    """
    locations = f"{origin['lat']},{origin['lon']}:{destination['lat']},{destination['lon']}"
    if departure_at <= datetime.now(UTC) + DEPART_NOW_MARGIN:
        depart_at = "now"
    else:
        depart_at = departure_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    data = _get(
        f"/routing/1/calculateRoute/{locations}/json",
        {
            "travelMode": "truck",
            "vehicleCommercial": "true",
            "traffic": "true",
            "departAt": depart_at,
            "vehicleWeight": gross_kg,
            "instructionsType": "coded",
            "maxAlternatives": 2,
        },
    )
    return [
        {
            "distance_mi": round(route["summary"]["lengthInMeters"] / METERS_PER_MILE, 1),
            "duration_s": route["summary"]["travelTimeInSeconds"],
            "geometry": [[p["longitude"], p["latitude"]] for leg in route["legs"] for p in leg["points"]],
            "instructions": [
                (i["routeOffsetInMeters"], i["travelTimeInSeconds"])
                for i in route.get("guidance", {}).get("instructions", [])
            ],
        }
        for route in data["routes"]
    ]
