from fastapi.testclient import TestClient

from news.api.app import app


def test_api_exposes_only_typed_plugin_creation_and_saved_draft_routes() -> None:
    response = TestClient(app).get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    collection = "/readers/{reader_id}/plugins/{plugin_id}/drafts"
    assert set(schema["paths"]) == {
        "/readers/{reader_id}/plugins",
        collection,
        collection + "/{draft_id}",
    }
    assert set(schema["paths"][collection + "/{draft_id}"]) == {"get", "put", "delete"}
    assert schema["paths"][collection]["post"]["responses"]["201"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/DraftDetails"}
