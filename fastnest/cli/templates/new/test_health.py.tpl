from fastapi.testclient import TestClient

from fastnest.core.factory import create_app
from src.app_module import AppModule


def test_health_check():
    app = create_app(AppModule)
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
