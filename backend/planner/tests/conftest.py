import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import requests
from django.core.cache import caches

FIXTURES = Path(__file__).parent / "fixtures"
FAKE_KEY = "test-tomtom-key"


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def fake_response(status, body):
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps(body).encode()
    return response


@pytest.fixture(autouse=True)
def tomtom_key(settings):
    settings.TOMTOM_API_KEY = FAKE_KEY


@pytest.fixture(autouse=True)
def empty_cache():
    for alias in caches:
        caches[alias].clear()


class Stub:
    """One upstream API. Set `.reply` to a response or an exception, or a list of them for successive calls.

    `.calls` records params.
    """

    reply = None

    def __init__(self):
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append({"url": url, "params": params})
        reply = self.reply.pop(0) if isinstance(self.reply, list) else self.reply
        if isinstance(reply, Exception):
            raise reply
        return reply


@pytest.fixture
def upstream(monkeypatch):
    """Stub every outbound `requests.get`, routed to a Stub by URL prefix."""
    stubs = {}

    def get(url, params=None, timeout=None):
        prefix = next((p for p in stubs if url.startswith(p)), None)
        assert prefix, f"Unstubbed request to {url}"
        return stubs[prefix].get(url, params, timeout)

    monkeypatch.setattr("requests.get", get)
    return stubs


@pytest.fixture
def tomtom(upstream):
    stub = upstream["https://api.tomtom.com"] = Stub()
    return stub


class OpenMeteoStub(Stub):
    """Replays the recorded forecast for any locations, re-dated to start today at 00:00 UTC like a live one.

    `.hourly` overrides series by name, with one value for every hour or a list of hourly values.
    `.issued_days_ago` starts the forecast on an earlier day, like one cached just before midnight UTC.
    The recorded values repeat to fill the requested `forecast_days`.
    """

    def __init__(self):
        super().__init__()
        self.hourly = {}
        self.issued_days_ago = 0

    def get(self, url, params=None, timeout=None):
        if (reply := super().get(url, params, timeout)) is not None:
            return reply
        recorded = load_fixture("openmeteo_forecast.json")
        midnight = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        start = midnight - timedelta(days=self.issued_days_ago)
        hours = int(params["forecast_days"]) * 24
        locations = []
        for i, (lat, lon) in enumerate(zip(params["latitude"].split(","), params["longitude"].split(","))):
            location = {**recorded[i % len(recorded)], "latitude": float(lat), "longitude": float(lon)}
            series = {k: v for k, v in location["hourly"].items() if k != "time"}
            location["hourly"] = {
                "time": [(start + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M") for h in range(hours)],
                **{k: [v[h % len(v)] for h in range(hours)] for k, v in series.items()},
                **{k: v if isinstance(v, list) else [v] * hours for k, v in self.hourly.items()},
            }
            locations.append(location)
        # Like the live API: a list for several locations, a bare object for one.
        return fake_response(200, locations if len(locations) > 1 else locations[0])


@pytest.fixture(autouse=True)
def openmeteo(upstream):
    stub = upstream["https://api.open-meteo.com"] = OpenMeteoStub()
    return stub
