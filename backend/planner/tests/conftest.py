import json
from pathlib import Path

import pytest
import requests
from django.core.cache import cache

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
    cache.clear()


@pytest.fixture
def tomtom(monkeypatch):
    """Stub the outbound HTTP call. Set `.reply` to a response or an exception; `.calls` records params."""

    class Stub:
        reply = None

        def __init__(self):
            self.calls = []

        def get(self, url, params=None, timeout=None):
            self.calls.append({"url": url, "params": params})
            if isinstance(self.reply, Exception):
                raise self.reply
            return self.reply

    stub = Stub()
    monkeypatch.setattr("planner.tomtom.requests.get", stub.get)
    return stub
