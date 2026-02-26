from fastapi.testclient import TestClient
from kb_desktop_daemon.config import Settings
from kb_desktop_daemon.http import create_app


def test_list_collection_documents_returns_404_for_missing_collection(tmp_path) -> None:
    settings = Settings(app_data_dir=str(tmp_path), auth_token="secret-token")
    app = create_app(settings=settings, auth_token="secret-token")
    client = TestClient(app)
    headers = {"Authorization": "Bearer secret-token"}

    response = client.get("/api/v1/collections/missing/documents", headers=headers)

    assert response.status_code == 404
