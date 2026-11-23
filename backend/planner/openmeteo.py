"""Hourly forecasts from Open-Meteo, cached per 0.1° grid point."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import requests
from django.core.cache import cache

URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = (5, 20)
HOUR = timedelta(hours=1)
CHUNK_SIZE = 100  # locations per request, keeps the URL short
MAX_PARALLEL = 4
CACHE_TTL_S = 60 * 60


class UpstreamError(Exception):
    """Open-Meteo failed or could not be reached."""


def snap(lat, lon):
    """The 0.1° grid point a lookup uses (PLAN.md A4)."""
    return round(lat, 1), round(lon, 1)


def get_hourly(points):
    """{(lat, lon): forecast} for snapped points. A forecast is {start, wind, gust, rain, snow} hourly lists.

    Each point is cached for an hour; misses are fetched in chunks, a few in parallel.
    """
    keys = {p: f"om:{p[0]:.1f}:{p[1]:.1f}" for p in points}
    cached = cache.get_many(keys.values())
    forecasts = {p: cached[key] for p, key in keys.items() if key in cached}
    missing = [p for p in keys if p not in forecasts]
    chunks = [missing[i : i + CHUNK_SIZE] for i in range(0, len(missing), CHUNK_SIZE)]
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as pool:
        for chunk, fetched in zip(chunks, pool.map(_fetch, chunks)):
            forecasts.update(zip(chunk, fetched))
    cache.set_many({keys[p]: forecasts[p] for p in missing}, CACHE_TTL_S)
    return forecasts


def _fetch(points):
    try:
        response = requests.get(
            URL,
            params={
                "latitude": ",".join(f"{lat:.1f}" for lat, _ in points),
                "longitude": ",".join(f"{lon:.1f}" for _, lon in points),
                "hourly": "wind_speed_10m,wind_gusts_10m,rain,showers,snowfall",
                "wind_speed_unit": "mph",
                "precipitation_unit": "inch",
                "timezone": "GMT",
                # 240 h covers a cached forecast from yesterday, a departure 5 days out (D12) and a ~95 h trip.
                "forecast_days": 10,
            },
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise UpstreamError(type(exc).__name__) from None
    if not response.ok:
        raise UpstreamError(f"Open-Meteo returned HTTP {response.status_code}")
    data = response.json()
    locations = data if isinstance(data, list) else [data]  # a single location comes back bare
    return [_forecast(location["hourly"]) for location in locations]


def _forecast(hourly):
    return {
        "start": datetime.fromisoformat(hourly["time"][0]).replace(tzinfo=UTC),
        "wind": hourly["wind_speed_10m"],
        "gust": hourly["wind_gusts_10m"],
        # Hourly sums over the preceding hour, so inches per hour (PLAN.md A5, checked live).
        "rain": [round(r + s, 3) for r, s in zip(hourly["rain"], hourly["showers"])],
        "snow": hourly["snowfall"],
    }


def weather_at(forecast, at):
    """The forecast hour nearest `at`, as checkpoint weather."""
    i = round((at - forecast["start"]) / HOUR)
    return {
        "wind_mph": forecast["wind"][i],
        "gust_mph": forecast["gust"][i],
        "rain_in_hr": forecast["rain"][i],
        "snow_in_hr": forecast["snow"][i],
    }
