from fastapi.testclient import TestClient
from kb_desktop_daemon.config import Settings
from kb_desktop_daemon.http import create_app


def test_document_view_endpoints_return_404_for_missing_document(tmp_path) -> None:
    settings = Settings(app_data_dir=str(tmp_path), auth_token="secret-token")
    app = create_app(settings=settings, auth_token="secret-token")
    client = TestClient(app)
    headers = {"Authorization": "Bearer secret-token"}

    original_resp = client.get("/api/v1/documents/missing/original", headers=headers)
    chunks_resp = client.get("/api/v1/documents/missing/chunks", headers=headers)

    assert original_resp.status_code == 404
    assert chunks_resp.status_code == 404
