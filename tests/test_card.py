from card import Card, Face


def test_from_json_maps_expected_fields():
    payload = {
        "name": "Aang, Air Nomad",
        "mana_cost": "{3}{W}{W}",
        "image_uris": {"art_crop": "https://example.com/aang.jpg"},
        "type_line": "Legendary Creature - Human Avatar Ally",
        "oracle_text": "Flying",
        "flavor_text": "Live with joy.",
        "power": "5",
        "toughness": "4",
    }

    card = Card.from_json(payload)

    assert card.name == "Aang, Air Nomad"
    assert len(card.faces) == 1
    face = card.faces[0]
    assert face.name == "Aang, Air Nomad"
    assert face.mana_cost == "{3}{W}{W}"
    assert face.cropped_image == "https://example.com/aang.jpg"
    assert face.typeline == "Legendary Creature - Human Avatar Ally"
    assert face.oracle_text == "Flying"
    assert face.flavor_text == "Live with joy."
    assert face.counter == "5/4"


def test_from_json_handles_missing_optional_fields():
    payload = {"name": "Nameless Monk"}

    card = Card.from_json(payload)

    assert card.name == "Nameless Monk"
    assert len(card.faces) == 1
    face = card.faces[0]
    assert face.name == "Nameless Monk"
    assert face.mana_cost is None
    assert face.cropped_image is None
    assert face.typeline is None
    assert face.oracle_text is None
    assert face.flavor_text is None
    assert face.counter is None


def test_from_json_ignores_non_dict_image_uris():
    payload = {
        "name": "Aang, Air Nomad",
        "image_uris": "not-a-dict",
    }

    card = Card.from_json(payload)

    assert card.faces[0].cropped_image is None


def test_from_json_requires_name():
    payload = {"mana_cost": "{W}"}

    try:
        Card.from_json(payload)
        assert False, "Expected ValueError for missing name"
    except ValueError as err:
        assert "name" in str(err)


def test_from_json_builds_multiple_faces_when_card_faces_present():
    payload = {
        "name": "Split Example",
        "card_faces": [
            {
                "name": "Front Face",
                "mana_cost": "{1}{U}",
                "type_line": "Creature - Wizard",
                "oracle_text": "Draw a card.",
                "power": "2",
                "toughness": "1",
                "image_uris": {"art_crop": "https://example.com/front.jpg"},
            },
            {
                "name": "Back Face",
                "mana_cost": "{2}{R}",
                "type_line": "Sorcery",
                "oracle_text": "Deal 3 damage.",
                "image_uris": {"art_crop": "https://example.com/back.jpg"},
            },
        ],
    }

    card = Card.from_json(payload)

    assert card.name == "Split Example"
    assert len(card.faces) == 2
    assert card.faces[0].name == "Front Face"
    assert card.faces[0].counter == "2/1"
    assert card.faces[1].name == "Back Face"
    assert card.faces[1].counter is None


def test_card_print_prints_all_faces_with_divider_between(monkeypatch):
    captured = {}

    def fake_send_print_job(payload):
        captured["payload"] = payload
        return {"ok": True}

    monkeypatch.setattr("card.send_print_job", fake_send_print_job)

    card = Card(
        name="Dual Card",
        faces=[
            Face(name="Front Face"),
            Face(name="Back Face"),
        ],
    )

    response = card.print()

    assert response == {"ok": True}
    assert "payload" in captured

    blocks = captured["payload"]["blocks"]
    assert [block["type"] for block in blocks] == ["text", "divider", "text"]
    assert blocks[0]["text"] == "Front Face"
    assert blocks[2]["text"] == "Back Face"
