from fastapi.testclient import TestClient

from news.api.app import app


def test_api_exposes_only_typed_plugin_draft_and_revision_routes() -> None:
    response = TestClient(app).get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    plugin = "/readers/{reader_id}/plugins/{plugin_id}"
    collection = plugin + "/drafts"
    assert set(schema["paths"]) == {
        "/readers/{reader_id}/plugins",
        collection,
        collection + "/{draft_id}",
        collection + "/{draft_id}/promote",
        plugin + "/revisions",
        plugin + "/current-revision",
    }
    assert set(schema["paths"][collection + "/{draft_id}/promote"]) == {"post"}
    assert set(schema["paths"][plugin + "/revisions"]) == {"get"}
    assert set(schema["paths"][plugin + "/current-revision"]) == {"put"}
    assert set(schema["paths"][collection + "/{draft_id}"]) == {"get", "put", "delete"}
    assert schema["paths"][collection]["post"]["responses"]["201"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/DraftDetails"}
