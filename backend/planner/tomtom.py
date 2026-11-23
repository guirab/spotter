from urllib.parse import quote

import requests
from django.conf import settings

BASE_URL = "https://api.tomtom.com"
TIMEOUT = (5, 20)
METERS_PER_MILE = 1609.344


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


def calculate_route(origin, destination):
    """Primary truck route as {distance_mi, duration_s, geometry: [[lon, lat], ...]}."""
    locations = f"{origin['lat']},{origin['lon']}:{destination['lat']},{destination['lon']}"
    data = _get(
        f"/routing/1/calculateRoute/{locations}/json",
        {"travelMode": "truck", "vehicleCommercial": "true", "traffic": "true"},
    )
    route = data["routes"][0]
    summary = route["summary"]
    return {
        "distance_mi": round(summary["lengthInMeters"] / METERS_PER_MILE, 1),
        "duration_s": summary["travelTimeInSeconds"],
        "geometry": [[p["longitude"], p["latitude"]] for leg in route["legs"] for p in leg["points"]],
    }
