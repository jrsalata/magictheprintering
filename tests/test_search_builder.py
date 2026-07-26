from search_builder import SearchBuilder


def test_build_url_single_card_accepts_api_host(monkeypatch):
    monkeypatch.setenv("SEARCH_URL", "https://api.scryfall.com")

    builder = SearchBuilder()
    url = builder.build_url_single_card()

    assert url.startswith("https://api.scryfall.com/cards/random?q=")


def test_build_url_single_card_accepts_cards_search_endpoint(monkeypatch):
    monkeypatch.setenv("SEARCH_URL", "https://api.scryfall.com/cards/search")

    builder = SearchBuilder()
    url = builder.build_url_single_card()

    assert url.startswith("https://api.scryfall.com/cards/random?q=")


def test_build_url_accepts_cards_path(monkeypatch):
    monkeypatch.setenv("SEARCH_URL", "https://api.scryfall.com/cards")

    builder = SearchBuilder()
    url = builder.build_url()

    assert url.startswith("https://api.scryfall.com/cards/search?q=")
