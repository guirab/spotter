from datetime import datetime, timedelta, timezone

import pytest
import requests
from django.utils.dateparse import parse_datetime

from planner.geo import haversine_mi

from .conftest import FAKE_KEY, fake_response, load_fixture

DENVER = {"label": "Denver, CO", "lat": 39.7392, "lon": -104.9903}
CHICAGO = {"label": "Chicago, IL", "lat": 41.8781, "lon": -87.6298}
PARIS = {"label": "Paris, France", "lat": 48.8566, "lon": 2.3522}


def next_hour():
    """A whole hour at least an hour away, clear of the 1-minute "send now" margin."""
    return (datetime.now(timezone.utc) + timedelta(hours=2)).replace(minute=0, second=0, microsecond=0)


def post_plan(client, origin, destination, **fields):
    body = {
        "origin": origin,
        "destination": destination,
        "departure_at": next_hour().isoformat(),
        "load_lb": 42000,
        "interval_mi": 25,
        **fields,
    }
    return client.post("/api/plan", body, content_type="application/json")


def test_returns_the_truck_route_parsed_from_tomtom(client, tomtom):
    tomtom.reply = fake_response(200, load_fixture("tomtom_route_denver_chicago.json"))

    response = post_plan(client, DENVER, CHICAGO)

    assert response.status_code == 200
    (route,) = response.json()["routes"]
    assert route["id"] == "A"
    assert route["distance_mi"] == 1005.0
    assert route["duration_s"] == 49999
    assert len(route["geometry"]) == 215
    assert route["geometry"][0] == [-104.99027, 39.7392]
    assert route["geometry"][-1] == [-87.62978, 41.8781]
    assert "instructions" not in route
    assert tomtom.calls[0]["params"]["travelMode"] == "truck"


def test_up_to_three_routes_come_back_ranked_with_a_recommendation(client, tomtom):
    tomtom.reply = fake_response(200, load_fixture("tomtom_routes_denver_chicago_3.json"))

    body = post_plan(client, DENVER, CHICAGO).json()

    assert len(tomtom.calls) == 1  # three distinct routes need no via-point fallback
    assert tomtom.calls[0]["params"]["maxAlternatives"] == 2
    routes = body["routes"]
    assert [(r["id"], r["rank"], r["distance_mi"]) for r in routes] == [
        ("A", 1, 1006.0),
        ("B", 2, 1173.2),
        ("C", 3, 1331.6),
    ]
    assert all(r["checkpoints"] and r["summary"]["max_level"] == "low" for r in routes)
    # The recorded forecast is calm everywhere, so travel time decides.
    assert body["recommended_route_id"] == "A"
    assert body["recommendation_reason"] == "Routes A and B have the same weather risk; Route A is 2 h 39 min faster."
    assert body["warnings"] == []


def via_reply(route):
    """`route` as TomTom returns it through a via-point: alone, split into two legs that share the via-point.

    Guidance stays as recorded: TomTom measures instruction offsets and times from the start of the route.
    """
    points = route["legs"][0]["points"]
    half = len(points) // 2
    return fake_response(200, {"routes": [{**route, "legs": [{"points": points[: half + 1]}, {"points": points[half:]}]}]})


def stops(call):
    """The [lon, lat] locations of a TomTom routing call."""
    return [[float(v) for v in reversed(stop.split(","))] for stop in call["url"].split("/")[-2].split(":")]


def test_a_single_route_is_topped_up_with_a_via_point_route_on_each_side(client, tomtom):
    alternatives = load_fixture("tomtom_routes_denver_chicago_3.json")["routes"]
    tomtom.reply = [
        fake_response(200, load_fixture("tomtom_route_denver_chicago.json")),
        via_reply(alternatives[1]),
        via_reply(alternatives[2]),
    ]
    departure = next_hour()

    body = post_plan(client, DENVER, CHICAGO, departure_at=departure.isoformat()).json()

    assert sorted((r["id"], r["distance_mi"]) for r in body["routes"]) == [("A", 1005.0), ("B", 1173.2), ("C", 1331.6)]
    assert body["warnings"] == []
    _, left, right = tomtom.calls
    origin, destination = [DENVER["lon"], DENVER["lat"]], [CHICAGO["lon"], CHICAGO["lat"]]
    assert [stops(left)[::2], stops(right)[::2]] == [[origin, destination]] * 2
    assert left["params"]["maxAlternatives"] == right["params"]["maxAlternatives"] == 0
    # Either side of the route, 15% of the 920 mi straight line away from it.
    left_via, right_via = stops(left)[1], stops(right)[1]
    assert haversine_mi(left_via, right_via) == pytest.approx(2 * 0.15 * haversine_mi(origin, destination), rel=0.05)
    assert haversine_mi(origin, left_via) == pytest.approx(haversine_mi(origin, right_via), rel=0.05)
    for route in body["routes"]:
        etas = [parse_datetime(c["eta"]) for c in route["checkpoints"]]
        assert etas == sorted(etas)
        assert abs(etas[-1] - (departure + timedelta(seconds=route["duration_s"]))) < timedelta(minutes=2)


def test_a_via_point_route_duplicating_one_already_found_is_dropped_and_a_warning_says_so(client, tomtom):
    single = load_fixture("tomtom_route_denver_chicago.json")
    alternatives = load_fixture("tomtom_routes_denver_chicago_3.json")["routes"]
    tomtom.reply = [fake_response(200, single), via_reply(single["routes"][0]), via_reply(alternatives[1])]

    body = post_plan(client, DENVER, CHICAGO).json()

    assert sorted((r["id"], r["distance_mi"]) for r in body["routes"]) == [("A", 1005.0), ("B", 1173.2)]
    assert body["warnings"] == ["Only 2 distinct routes found."]


def test_a_via_point_route_that_covers_one_already_found_plus_a_detour_is_dropped(client, tomtom):
    single = load_fixture("tomtom_route_denver_chicago.json")
    primary = single["routes"][0]
    points = primary["legs"][0]["points"]
    half = len(points) // 2
    # ~100 mi north of the route's midpoint and back: the primary lies entirely along this one, not the reverse.
    lat, lon = points[half]["latitude"], points[half]["longitude"]
    detour = [{"latitude": lat + d, "longitude": lon} for d in (0.75, 1.5, 0.75)]
    with_detour = {**primary, "legs": [{"points": points[: half + 1] + detour + points[half:]}]}
    tomtom.reply = [fake_response(200, single), via_reply(with_detour), requests.ConnectionError("unreachable")]

    body = post_plan(client, DENVER, CHICAGO).json()

    assert [r["id"] for r in body["routes"]] == ["A"]


def test_via_point_calls_that_fail_are_skipped(client, tomtom):
    no_route = load_fixture("tomtom_route_no_route.json")
    tomtom.reply = [
        fake_response(200, load_fixture("tomtom_route_denver_chicago.json")),
        fake_response(no_route["status"], no_route["body"]),
        requests.ConnectionError("unreachable"),
    ]

    response = post_plan(client, DENVER, CHICAGO)

    assert response.status_code == 200
    assert [r["id"] for r in response.json()["routes"]] == ["A"]
    assert response.json()["warnings"] == ["Only 1 distinct route found."]


def test_tomtom_gets_the_departure_and_gross_weight_in_kg(client, tomtom):
    tomtom.reply = fake_response(200, load_fixture("tomtom_route_denver_chicago.json"))
    departure = next_hour()

    post_plan(client, DENVER, CHICAGO, departure_at=departure.isoformat(), load_lb=42000)

    params = tomtom.calls[0]["params"]
    assert params["departAt"] == departure.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert params["vehicleWeight"] == 34927  # (42,000 lb load + 35,000 lb tare) in kg
    assert params["instructionsType"] == "coded"


@pytest.mark.parametrize("offset", [timedelta(minutes=-10), timedelta(seconds=30)])
def test_a_departure_that_just_passed_or_is_imminent_is_sent_as_now(client, tomtom, offset):
    # TomTom rejects a departure in the past, which a timestamp under a minute ahead can become in transit.
    tomtom.reply = fake_response(200, load_fixture("tomtom_route_denver_chicago.json"))

    response = post_plan(client, DENVER, CHICAGO, departure_at=(datetime.now(timezone.utc) + offset).isoformat())

    assert response.status_code == 200
    assert tomtom.calls[0]["params"]["departAt"] == "now"


def test_checkpoints_carry_mile_position_and_utc_eta(client, tomtom):
    tomtom.reply = fake_response(200, load_fixture("tomtom_route_denver_chicago.json"))
    departure = next_hour()

    response = post_plan(client, DENVER, CHICAGO, departure_at=departure.isoformat(), interval_mi=25)

    checkpoints = response.json()["routes"][0]["checkpoints"]
    assert [c["mile"] for c in checkpoints] == [*range(0, 1001, 25), 1005.0]
    assert sum(c["segment_mi"] for c in checkpoints) == pytest.approx(1005.0, abs=0.05)
    first, last = checkpoints[0], checkpoints[-1]
    assert (first["lat"], first["lon"]) == (39.7392, -104.99027)
    assert (last["lat"], last["lon"]) == (41.8781, -87.62978)
    assert first["eta"] == departure.strftime("%Y-%m-%dT%H:%M:%SZ")
    arrival = departure + timedelta(seconds=49999)
    assert abs(parse_datetime(last["eta"]) - arrival) < timedelta(minutes=1)
    assert last["eta"].endswith("Z")


def test_a_wider_interval_means_fewer_checkpoints(client, tomtom):
    tomtom.reply = fake_response(200, load_fixture("tomtom_route_denver_chicago.json"))

    response = post_plan(client, DENVER, CHICAGO, interval_mi=50)

    assert len(response.json()["routes"][0]["checkpoints"]) == 22  # 0, 50, …, 1000, 1005


def test_checkpoints_carry_the_weather_of_the_hour_nearest_their_eta(client, tomtom, openmeteo):
    tomtom.reply = fake_response(200, load_fixture("tomtom_route_denver_chicago.json"))
    # Wind equals the hour's index in the forecast, which starts today at 00:00 UTC.
    openmeteo.hourly = {"wind_speed_10m": list(range(192)), "wind_gusts_10m": 70, "rain": 0.05, "showers": 0.03}
    departure = next_hour()
    midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    departure_hour = (departure - midnight) // timedelta(hours=1)

    response = post_plan(client, DENVER, CHICAGO, departure_at=departure.isoformat())

    checkpoints = response.json()["routes"][0]["checkpoints"]
    assert checkpoints[0]["weather"] == {
        "wind_mph": departure_hour,
        "gust_mph": 70,
        "rain_in_hr": 0.08,  # rain + showers
        "snow_in_hr": 0.0,
    }
    # Arrival is 13 h 53 min after departure, nearest to the 14th hour.
    assert checkpoints[-1]["weather"]["wind_mph"] == departure_hour + 14


def test_a_long_trip_departing_in_5_days_on_yesterdays_forecast_still_gets_weather(client, tomtom, openmeteo):
    # Stretch the route to 60 h of driving.
    route = load_fixture("tomtom_route_denver_chicago.json")
    summary, instructions = route["routes"][0]["summary"], route["routes"][0]["guidance"]["instructions"]
    scale = 60 * 3600 / summary["travelTimeInSeconds"]
    summary["travelTimeInSeconds"] = 60 * 3600
    for instruction in instructions:
        instruction["travelTimeInSeconds"] = round(instruction["travelTimeInSeconds"] * scale)
    tomtom.reply = fake_response(200, route)
    openmeteo.issued_days_ago = 1
    departure = (datetime.now(timezone.utc) + timedelta(days=5) - timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

    response = post_plan(client, DENVER, CHICAGO, departure_at=departure.isoformat())

    assert response.status_code == 200
    assert response.json()["routes"][0]["checkpoints"][-1]["weather"] is not None


def test_a_heavier_load_raises_a_windy_checkpoint_and_names_the_load_rule(client, tomtom, openmeteo):
    tomtom.reply = fake_response(200, load_fixture("tomtom_route_denver_chicago.json"))
    openmeteo.hourly = {"wind_speed_10m": 38}

    light = post_plan(client, DENVER, CHICAGO, load_lb=30_000).json()["routes"][0]["checkpoints"][0]
    heavy = post_plan(client, DENVER, CHICAGO, load_lb=45_000).json()["routes"][0]["checkpoints"][0]

    assert (light["level"], light["score"], light["reasons"]) == ("high", 2, ["Wind 38 mph → High"])
    assert (heavy["level"], heavy["score"]) == ("severe", 3)
    assert heavy["reasons"][-1] == "Load rule: 35–44 mph & >40,000 lb → Severe"


def test_open_meteo_gets_snapped_points_in_chunks_of_100(client, tomtom, openmeteo):
    tomtom.reply = fake_response(200, load_fixture("tomtom_route_denver_chicago.json"))

    response = post_plan(client, DENVER, CHICAGO, interval_mi=10)

    checkpoints = response.json()["routes"][0]["checkpoints"]
    snapped = {(f"{c['lat']:.1f}", f"{c['lon']:.1f}") for c in checkpoints}
    requested = [
        point
        for call in openmeteo.calls
        for point in zip(call["params"]["latitude"].split(","), call["params"]["longitude"].split(","))
    ]
    assert sorted(requested) == sorted(snapped)  # each grid point once
    assert [len(call["params"]["latitude"].split(",")) for call in openmeteo.calls] == [100, len(snapped) - 100]
    params = openmeteo.calls[0]["params"]
    assert (params["wind_speed_unit"], params["precipitation_unit"], params["timezone"]) == ("mph", "inch", "GMT")


def test_repeating_a_plan_within_the_hour_reuses_cached_weather(client, tomtom, openmeteo):
    tomtom.reply = fake_response(200, load_fixture("tomtom_route_denver_chicago.json"))
    post_plan(client, DENVER, CHICAGO)
    calls = len(openmeteo.calls)

    response = post_plan(client, DENVER, CHICAGO)

    assert response.status_code == 200
    assert len(openmeteo.calls) == calls


def test_weather_failure_is_a_502(client, tomtom, openmeteo):
    tomtom.reply = fake_response(200, load_fixture("tomtom_route_denver_chicago.json"))
    openmeteo.reply = fake_response(503, {"error": True})

    response = post_plan(client, DENVER, CHICAGO)

    assert response.status_code == 502
    assert "weather" in response.json()["detail"]


@pytest.mark.parametrize(
    "field, value",
    [
        ("departure_at", lambda: (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()),
        ("departure_at", lambda: (datetime.now(timezone.utc) + timedelta(days=5, minutes=5)).isoformat()),
        ("load_lb", lambda: -1),
        ("load_lb", lambda: 80001),
        ("interval_mi", lambda: 30),
    ],
)
def test_out_of_range_inputs_are_field_errors(client, field, value):
    response = post_plan(client, DENVER, CHICAGO, **{field: value()})

    assert response.status_code == 400
    assert field in response.json()


def test_no_route_between_the_places_is_a_422(client, tomtom):
    recorded = load_fixture("tomtom_route_no_route.json")
    tomtom.reply = fake_response(recorded["status"], recorded["body"])

    response = post_plan(client, {"label": "Honolulu, HI", "lat": 21.3069, "lon": -157.8583}, DENVER)

    assert response.status_code == 422
    assert "detail" in response.json()


def test_origin_outside_the_us_is_a_field_error(client):
    response = post_plan(client, PARIS, CHICAGO)

    assert response.status_code == 400
    assert "origin" in response.json()


def test_same_origin_and_destination_is_a_field_error(client):
    response = post_plan(client, DENVER, {**DENVER, "label": "Denver"})

    assert response.status_code == 400
    assert "destination" in response.json()


def test_upstream_failure_is_a_502_without_leaking_the_key(client, tomtom):
    tomtom.reply = requests.ConnectionError(f"Max retries exceeded with url: /routing?key={FAKE_KEY}")

    response = post_plan(client, DENVER, CHICAGO)

    assert response.status_code == 502
    assert FAKE_KEY not in response.content.decode()
