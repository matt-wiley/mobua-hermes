from fastapi.testclient import TestClient

from news.api.app import app


def test_api_app_starts_with_no_routes_yet() -> None:
    response = TestClient(app).get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["paths"] == {}
