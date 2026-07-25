import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_hello_world(client):
    response = client.get("/", data={"action": "hello"})
    assert response.status_code == 200
    assert b"Print Hello World" in response.data


def test_print_hello_world(client, monkeypatch):
    sent = []
    monkeypatch.setattr("app.send_print_job", lambda payload: sent.append(payload))
    response = client.post("/", data={"action": "hello"})
    assert response.status_code == 200
    assert b"Print job sent!" in response.data
    assert sent == [{"blocks": [{"type": "text", "text": "Hello, World!"}]}]

def test_print_fortune(client, monkeypatch):
    sent = []
    monkeypatch.setattr("app.send_print_job", lambda payload: sent.append(payload))
    response = client.post("/", data={"action": "fortune"})
    assert response.status_code == 200
    assert b"Print job sent!" in response.data
    assert len(sent) == 1
    assert sent[0]["blocks"][0]["type"] == "text"
