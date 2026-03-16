from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_comics_empty():
    response = client.get("/comics/")
    assert response.status_code == 200
    assert "Комиксы" in response.text