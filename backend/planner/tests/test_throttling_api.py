import pytest
from django.core.cache import cache


def post_plan(client, **headers):
    return client.post("/api/plan", {}, content_type="application/json", **headers)


def get_geocode(client, **headers):
    return client.get("/api/geocode", {"q": "de"}, **headers)  # too short, so TomTom is never called


@pytest.mark.parametrize("send, allowed_per_minute", [(post_plan, 20), (get_geocode, 60)])
def test_requests_past_the_limit_are_a_429_that_says_when_to_retry(client, send, allowed_per_minute):
    within = [send(client).status_code for _ in range(allowed_per_minute)]
    over = send(client)

    assert set(within) == {400}
    assert over.status_code == 429
    assert "detail" in over.json()
    assert 0 < int(over.headers["Retry-After"]) <= 60


def test_a_forged_forwarded_for_does_not_escape_the_limit(client):
    # The proxy in front of the app appends the real client to whatever the client sent.
    codes = [post_plan(client, HTTP_X_FORWARDED_FOR=f"10.0.0.{i}, 203.0.113.7").status_code for i in range(21)]

    assert codes[-1] == 429


def test_clients_are_limited_separately(client):
    for _ in range(21):
        post_plan(client, HTTP_X_FORWARDED_FOR="203.0.113.7")

    assert post_plan(client, HTTP_X_FORWARDED_FOR="203.0.113.8").status_code == 400


def test_a_burst_of_cached_weather_does_not_reset_the_limit(client):
    # One heatmap caches up to 400 weather points, over the cache's 300-entry default, which evicts others.
    for _ in range(20):
        post_plan(client)
    for i in range(400):
        cache.set(f"om:{i}", {})

    assert post_plan(client).status_code == 429
