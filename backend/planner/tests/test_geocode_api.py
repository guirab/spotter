from .conftest import fake_response, load_fixture


def test_returns_us_places_for_the_query(client, tomtom):
    tomtom.reply = fake_response(200, load_fixture("tomtom_geocode_denver.json"))

    response = client.get("/api/geocode", {"q": "denver"})

    assert response.status_code == 200
    places = response.json()
    assert len(places) == 5
    assert places[0] == {"label": "Denver, CO", "lat": 39.738453, "lon": -104.984853}
    assert tomtom.calls[0]["params"]["countrySet"] == "US"


def test_repeated_queries_are_served_from_cache(client, tomtom):
    tomtom.reply = fake_response(200, load_fixture("tomtom_geocode_denver.json"))

    first = client.get("/api/geocode", {"q": "Denver"})
    second = client.get("/api/geocode", {"q": " denver "})

    assert second.json() == first.json()
    assert len(tomtom.calls) == 1


def test_tomtom_errors_are_a_502(client, tomtom):
    tomtom.reply = fake_response(403, {"errorText": "Forbidden"})

    response = client.get("/api/geocode", {"q": "denver"})

    assert response.status_code == 502


def test_short_queries_are_rejected_without_calling_tomtom(client, tomtom):
    response = client.get("/api/geocode", {"q": "de "})

    assert response.status_code == 400
    assert "q" in response.json()
    assert tomtom.calls == []
