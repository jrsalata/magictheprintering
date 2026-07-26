from io import BytesIO

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


def test_search_form_on_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b'action="/search"' in response.data
    assert b'name="card_name"' in response.data


def test_deck_form_on_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b'action="/deck"' in response.data
    assert b'name="deck_file"' in response.data


def test_filter_form_on_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b'action="/filter"' in response.data
    assert b'name="colors"' in response.data
    assert b'name="rarity"' in response.data
    assert b'name="format"' in response.data


def test_search_prints_fuzzy_matched_card(client, monkeypatch):
    sent = []
    fetched = []

    def fake_fetch_card(card_name):
        fetched.append(card_name)
        return {"name": "Lightning Bolt", "type_line": "Instant"}

    monkeypatch.setattr("app.fetch_card", fake_fetch_card)
    monkeypatch.setattr("card.send_print_job", lambda payload: sent.append(payload) or {"success": True})

    response = client.post("/search", data={"card_name": "lightn bolt"})

    assert response.status_code == 200
    assert b"Printed Lightning Bolt" in response.data
    assert fetched == ["lightn bolt"]
    assert len(sent) == 1
    assert sent[0]["blocks"][0]["text"] == "Lightning Bolt"


def test_search_missing_name_returns_400(client):
    response = client.post("/search", data={"card_name": "   "})
    assert response.status_code == 400
    assert b"No card name provided." in response.data


def test_search_no_match_shows_scryfall_details(client, monkeypatch):
    sent = []

    def fake_fetch_card(_card_name):
        raise HttpRequestError(
            source="scryfall",
            status_code=404,
            details="No cards found matching “not a real card”",
            url="https://api.scryfall.com/cards/named?fuzzy=not%20a%20real%20card",
        )

    monkeypatch.setattr("app.fetch_card", fake_fetch_card)
    monkeypatch.setattr("app.send_print_job", lambda payload: sent.append(payload) or {"success": True})

    response = client.post("/search", data={"card_name": "not a real card"})

    assert response.status_code == 404
    assert "No cards found matching “not a real card”".encode("utf-8") in response.data
    assert sent == []


def test_deck_prints_all_cards_after_all_lookups_succeed(client, monkeypatch):
    sent = []
    fetched = []

    def fake_fetch_card(card_name):
        fetched.append(card_name)
        return {"name": card_name, "type_line": "Instant"}

    monkeypatch.setattr("app.fetch_card", fake_fetch_card)
    monkeypatch.setattr("card.send_print_job", lambda payload: sent.append(payload) or {"success": True})

    response = client.post(
        "/deck",
        data={"deck_file": (BytesIO(b"Lightning Bolt\nCounterspell\n"), "deck.txt")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert b"Printed 2 cards." in response.data
    assert fetched == ["Lightning Bolt", "Counterspell"]
    assert [payload["blocks"][0]["text"] for payload in sent] == ["Lightning Bolt", "Counterspell"]


def test_deck_missing_file_returns_400(client):
    response = client.post("/deck", data={}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert b"No deck file provided." in response.data


def test_deck_empty_file_returns_400(client):
    response = client.post(
        "/deck",
        data={"deck_file": (BytesIO(b"\n  \n"), "deck.txt")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert b"Deck file did not contain any card names." in response.data


def test_deck_lookup_failure_stops_printing(client, monkeypatch):
    sent = []
    fetched = []

    def fake_fetch_card(card_name):
        fetched.append(card_name)
        if card_name == "Not A Real Card":
            raise HttpRequestError(
                source="scryfall",
                status_code=404,
                details="No cards found matching “Not A Real Card”",
                url="https://api.scryfall.com/cards/named?fuzzy=Not%20A%20Real%20Card",
            )
        return {"name": card_name, "type_line": "Instant"}

    monkeypatch.setattr("app.fetch_card", fake_fetch_card)
    monkeypatch.setattr("card.send_print_job", lambda payload: sent.append(payload) or {"success": True})

    response = client.post(
        "/deck",
        data={"deck_file": (BytesIO(b"Lightning Bolt\nNot A Real Card\n"), "deck.txt")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 404
    assert "No cards found matching “Not A Real Card”".encode("utf-8") in response.data
    assert fetched == ["Lightning Bolt", "Not A Real Card"]
    assert sent == []


def test_filter_prints_matching_card(client, monkeypatch):
    sent = []
    seen_urls = []

    def fake_fetch_json(url):
        seen_urls.append(url)
        return {"name": "Llanowar Elves", "type_line": "Creature — Elf Druid"}

    monkeypatch.setattr("app.fetch_json", fake_fetch_json)
    monkeypatch.setattr("card.send_print_job", lambda payload: sent.append(payload) or {"success": True})

    response = client.post(
        "/filter",
        data={
            "card_type": "creature",
            "mana_value_comparison": "=",
            "mana_value": "1",
            "colors": ["g"],
            "rarity_comparison": "=",
            "rarity": "common",
            "format": "commander",
            "exclude_lands": "enabled",
        },
    )

    assert response.status_code == 200
    assert b"Printed Llanowar Elves" in response.data
    assert len(seen_urls) == 1
    query = seen_urls[0]
    assert "t%3Acreature" in query
    assert "mv%3D1" in query
    assert "c%3Ag" in query
    assert "r%3Dcommon" in query
    assert "f%3Acommander" in query
    assert "-type%3Aland" in query
    assert len(sent) == 1
    assert sent[0]["blocks"][0]["text"] == "Llanowar Elves"


def test_filter_invalid_rarity_returns_400(client):
    response = client.post("/filter", data={"rarity": "legendary"})
    assert response.status_code == 400
    assert b"Invalid rarity" in response.data


def test_filter_no_match_shows_404(client, monkeypatch):
    def fake_fetch_json(_url):
        raise HttpRequestError(
            source="search_results",
            status_code=404,
            details="No cards found",
            url="https://api.example.test/random",
        )

    monkeypatch.setattr("app.fetch_json", fake_fetch_json)

    response = client.post("/filter", data={"card_type": "sorcery"})

    assert response.status_code == 404
    assert b"No cards found" in response.data


def test_search_http_error_prints_error_receipt(client, monkeypatch):
    sent = []

    def fake_fetch_card(_card_name):
        raise HttpRequestError(
            source="scryfall",
            status_code=503,
            details="Service unavailable",
            url="https://api.scryfall.com/cards/named?fuzzy=bolt",
        )

    monkeypatch.setattr("app.fetch_card", fake_fetch_card)
    monkeypatch.setattr("app.send_print_job", lambda payload: sent.append(payload) or {"success": True})

    response = client.post("/search", data={"card_name": "bolt"})

    assert response.status_code == 502
    assert b"Error receipt sent to printer" in response.data
    assert len(sent) == 1
    assert sent[0]["blocks"][0]["text"] == "HTTP Server Error"


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
    rendered_text = "\n".join(
        block.get("text", "")
        for block in sent[0]["blocks"]
        if isinstance(block, dict)
    )
    assert "404" in rendered_text
