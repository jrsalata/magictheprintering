from card import Card


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
    assert card.mana_cost == "{3}{W}{W}"
    assert card.cropped_image == "https://example.com/aang.jpg"
    assert card.typeline == "Legendary Creature - Human Avatar Ally"
    assert card.oracle_text == "Flying"
    assert card.flavor_text == "Live with joy."
    assert card.counter == "5/4"


def test_from_json_handles_missing_optional_fields():
    payload = {"name": "Nameless Monk"}

    card = Card.from_json(payload)

    assert card.name == "Nameless Monk"
    assert card.mana_cost is None
    assert card.cropped_image is None
    assert card.typeline is None
    assert card.oracle_text is None
    assert card.flavor_text is None
    assert card.counter is None


def test_from_json_ignores_non_dict_image_uris():
    payload = {
        "name": "Aang, Air Nomad",
        "image_uris": "not-a-dict",
    }

    card = Card.from_json(payload)

    assert card.cropped_image is None


def test_from_json_requires_name():
    payload = {"mana_cost": "{W}"}

    try:
        Card.from_json(payload)
        assert False, "Expected ValueError for missing name"
    except ValueError as err:
        assert "name" in str(err)
