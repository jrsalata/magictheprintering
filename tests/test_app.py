import pytest
from app import app
from http_errors import HttpRequestError


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
    monkeypatch.setattr("app.build_hello_world_blocks", lambda: {"blocks": [{"type": "text", "text": "Hello, World!"}]})
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

def test_discord_form_on_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b'action="/discord"' in response.data
    assert b'name="illegal_cards"' in response.data


def test_root_http_error_prints_error_receipt(client, monkeypatch):
    calls = []

    def fake_send_print_job(payload):
        calls.append(payload)
        if len(calls) == 1:
            raise HttpRequestError(
                source="printer_api",
                status_code=503,
                details="Service unavailable",
                url="http://printer.local/builder",
            )
        return {"success": True}

    monkeypatch.setattr("app.send_print_job", fake_send_print_job)
    monkeypatch.setattr("app.build_hello_world_blocks", lambda: {"blocks": [{"type": "text", "text": "Hello"}]})

    response = client.post("/", data={"action": "hello"})

    assert response.status_code == 200
    assert b"Error receipt sent to printer" in response.data
    assert len(calls) == 2
    assert calls[1]["blocks"][0]["text"] == "HTTP Server Error"


def test_momir_http_error_prints_error_receipt(client, monkeypatch):
    sent = []

    class FakeSearchBuilder:
        def add_card_type(self, _card_type):
            return None

        def add_mana_value(self, _value):
            return None

        def build_url_single_card(self):
            return "https://api.example.test/random"

    def fake_fetch_json(_url):
        raise HttpRequestError(
            source="search_results",
            status_code=404,
            details="No cards found",
            url="https://api.example.test/random",
        )

    monkeypatch.setattr("app.SearchBuilder", FakeSearchBuilder)
    monkeypatch.setattr("app.fetch_json", fake_fetch_json)
    monkeypatch.setattr("app.send_print_job", lambda payload: sent.append(payload) or {"success": True})

    response = client.post("/momir", data={"mana_value": "3"})

    assert response.status_code == 502
    assert b"Error receipt sent to printer" in response.data
    assert len(sent) == 1
    assert sent[0]["blocks"][0]["text"] == "Not Found (404)"
