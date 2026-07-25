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


def test_momir_form_on_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b'action="/momir"' in response.data
    assert b'name="mana_value"' in response.data


def test_submit_momir_valid(client, monkeypatch):
    sent = []
    monkeypatch.setattr("app.send_print_momir", lambda payload: sent.append(payload))
    response = client.post("/momir", data={"mana_value": "42"})
    assert response.status_code == 200
    assert b"Printing random creature with mana value" in response.data


def test_submit_momir_decimal(client, monkeypatch):
    sent = []
    monkeypatch.setattr("app.send_print_momir", lambda payload: sent.append(payload))
    response = client.post("/momir", data={"mana_value": "3.14"})
    assert response.status_code == 400
    assert b"Invalid mana value" in response.data


def test_submit_momir_invalid(client, monkeypatch):
    sent = []
    monkeypatch.setattr("app.send_print_momir", lambda payload: sent.append(payload))
    response = client.post("/momir", data={"mana_value": "not-a-number"})
    assert response.status_code == 400
    assert b"Invalid mana value" in response.data
