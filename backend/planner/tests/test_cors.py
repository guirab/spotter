import pytest

FRONTEND_ORIGIN = "https://frontend.example.com"


@pytest.fixture(autouse=True)
def frontend_origin(settings):
    settings.CORS_ALLOWED_ORIGINS = [FRONTEND_ORIGIN]


def test_configured_frontend_origin_may_call_the_api(client):
    response = client.get("/api/health", HTTP_ORIGIN=FRONTEND_ORIGIN)

    assert response.headers["Access-Control-Allow-Origin"] == FRONTEND_ORIGIN


def test_other_origins_are_not_allowed(client):
    response = client.get("/api/health", HTTP_ORIGIN="https://evil.example.com")

    assert "Access-Control-Allow-Origin" not in response.headers
