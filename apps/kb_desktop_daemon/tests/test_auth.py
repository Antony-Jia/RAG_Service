from fastapi.testclient import TestClient
from kb_desktop_daemon.config import Settings
from kb_desktop_daemon.http import create_app


def test_api_requires_token(tmp_path) -> None:
    settings = Settings(app_data_dir=str(tmp_path), auth_token="secret-token")
    app = create_app(settings=settings, auth_token="secret-token")
    client = TestClient(app)

    response = client.get("/api/v1/capabilities")
    assert response.status_code == 401

    ok = client.get("/api/v1/capabilities", headers={"Authorization": "Bearer secret-token"})
    assert ok.status_code == 200
