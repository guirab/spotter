import requests

from .conftest import FAKE_KEY, fake_response, load_fixture

DENVER ={"label": "Denver, CO", "lat": 39.7392, "lon": -104.9903}
CHICAGO = {"label": "Chicago, IL", "lat": 41.8781, "lon": -87.6298}
PARIS = {"label": "Paris, France", "lat": 48.8566, "lon": 2.3522}


def post_plan(client, origin, destination):
    return client.post(
        "/api/plan", {"origin": origin, "destination": destination}, content_type="application/json"
    )


def test_returns_the_truck_route_parsed_from_tomtom(client, tomtom):
    tomtom.reply = fake_response(200, load_fixture("tomtom_route_denver_chicago.json"))

    response = post_plan(client, DENVER, CHICAGO)

    assert response.status_code == 200
    (route,) = response.json()["routes"]
    assert route["id"] == "A"
    assert route["distance_mi"] == 1005.9
    assert route["duration_s"] == 49387
    assert len(route["geometry"]) == 214
    assert route["geometry"][0] == [-104.99027, 39.7392]
    assert route["geometry"][-1] == [-87.62978, 41.8781]
    assert tomtom.calls[0]["params"]["travelMode"] == "truck"


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
