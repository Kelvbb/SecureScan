import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_respirer_returns_ok(client):
    response = client.get("/respirer")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert "message" in data
