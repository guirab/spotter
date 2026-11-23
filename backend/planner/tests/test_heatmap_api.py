from datetime import UTC, datetime, timedelta
from math import ceil

from django.core.cache import cache

from planner.geo import haversine_mi

from .conftest import fake_response, load_fixture
from .test_plan_api import CHICAGO, DENVER, next_hour, post_plan


def plan_id_for(client, tomtom, fixture="tomtom_route_denver_chicago.json", **fields):
    tomtom.reply = fake_response(200, load_fixture(fixture))
    return post_plan(client, DENVER, CHICAGO, **fields).json()["plan_id"]


def get_heatmap(client, plan_id):
    return client.get("/api/heatmap", {"plan_id": plan_id})


def densified(line, step_mi=0.25):
    """The line's vertices plus points at most `step_mi` apart in between."""
    points = [line[0]]
    for a, b in zip(line, line[1:]):
        n = max(1, ceil(haversine_mi(a, b) / step_mi))
        points += [[a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n] for k in range(1, n + 1)]
    return points


def test_a_plan_has_a_heatmap_of_49_hourly_scores_per_node_from_departure(client, tomtom):
    departure = next_hour() + timedelta(minutes=30)
    plan_id = plan_id_for(client, tomtom, departure_at=departure.isoformat())

    response = get_heatmap(client, plan_id)

    assert response.status_code == 200
    body = response.json()
    assert body["start_at"] == departure.replace(minute=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert body["spacing_deg"] == 0.25
    assert body["points"] and len(body["scores"]) == len(body["points"])
    assert all(len(hours) == 49 for hours in body["scores"])
    # The recorded forecast is calm everywhere.
    assert {s for hours in body["scores"] for s in hours} == {0}


def test_an_unknown_or_expired_plan_is_a_404(client, tomtom):
    plan_id = plan_id_for(client, tomtom)
    cache.delete(f"plan:{plan_id}")  # what the 1 h TTL does

    for unknown in [plan_id, "not-a-plan-id", ""]:
        response = get_heatmap(client, unknown)

        assert response.status_code == 404
        assert "detail" in response.json()


def test_nodes_lie_on_the_lattice_within_25_miles_of_a_route(client, tomtom):
    tomtom.reply = fake_response(200, load_fixture("tomtom_routes_denver_chicago_3.json"))
    plan = post_plan(client, DENVER, CHICAGO).json()

    body = get_heatmap(client, plan["plan_id"]).json()

    spacing = body["spacing_deg"]
    route_points = [p for r in plan["routes"] for p in densified(r["geometry"])]
    for lon, lat in body["points"]:
        assert (lon / spacing).is_integer() and (lat / spacing).is_integer()
        assert min(haversine_mi((lon, lat), p) for p in route_points) <= 25.125  # half a densify step
    # The corridor reaches both ends of the trip.
    assert any(haversine_mi(p, (DENVER["lon"], DENVER["lat"])) <= 25 for p in body["points"])
    assert any(haversine_mi(p, (CHICAGO["lon"], CHICAGO["lat"])) <= 25 for p in body["points"])


def test_a_corridor_over_the_node_cap_coarsens_the_lattice(client, tomtom, monkeypatch):
    plan_id = plan_id_for(client, tomtom)
    fine = get_heatmap(client, plan_id).json()
    monkeypatch.setattr("planner.heatmap.MAX_NODES", len(fine["points"]) - 1)

    coarse = get_heatmap(client, plan_id).json()

    assert (fine["spacing_deg"], coarse["spacing_deg"]) == (0.25, 0.5)
    assert len(coarse["points"]) < len(fine["points"])


def test_the_same_corridor_gets_the_same_nodes_in_every_plan(client, tomtom, openmeteo):
    first = get_heatmap(client, plan_id_for(client, tomtom)).json()
    calls = len(openmeteo.calls)

    second = get_heatmap(client, plan_id_for(client, tomtom, load_lb=10_000)).json()

    assert second["points"] == first["points"]
    assert len(openmeteo.calls) == calls  # so the weather comes from the cache


def test_scores_follow_the_forecast_hour_by_hour_and_the_load(client, tomtom, openmeteo):
    # Wind equals the hour's index in the forecast, which starts today at 00:00 UTC.
    openmeteo.hourly = {"wind_speed_10m": list(range(240))}
    departure = next_hour()
    departure_hour = departure.hour + (departure.date() - datetime.now(UTC).date()).days * 24

    def first_node_scores(load_lb):
        plan_id = plan_id_for(client, tomtom, departure_at=departure.isoformat(), load_lb=load_lb)
        return get_heatmap(client, plan_id).json()["scores"][0]

    light, heavy = first_node_scores(30_000), first_node_scores(45_000)

    def score_at(scores, wind):
        return scores[wind - departure_hour]

    assert len(light) == 49
    # 24 → Low, 25 → Moderate, 35 → High, 45 → Severe, 55 → No Travel; heavy loads go up a step in 35–54 mph.
    winds = [w for w in (24, 25, 35, 45, 55) if 0 <= w - departure_hour < 49]
    expected_light = {24: 0, 25: 1, 35: 2, 45: 3, 55: 4}
    expected_heavy = {24: 0, 25: 1, 35: 3, 45: 4, 55: 4}
    assert [score_at(light, w) for w in winds] == [expected_light[w] for w in winds]
    assert [score_at(heavy, w) for w in winds] == [expected_heavy[w] for w in winds]
    assert winds  # the departure is within a day, so the window always covers some thresholds


def test_weather_failure_is_a_502(client, tomtom, openmeteo):
    plan_id = plan_id_for(client, tomtom)  # caches only the checkpoints' weather, not the whole corridor's
    openmeteo.reply = fake_response(503, {"error": True})

    response = get_heatmap(client, plan_id)

    assert response.status_code == 502
