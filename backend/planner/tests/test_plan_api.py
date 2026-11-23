from datetime import datetime, timedelta, timezone

import pytest
import requests
from django.utils.dateparse import parse_datetime

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
