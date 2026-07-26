import json
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

from dotenv import load_dotenv

from card import Card
from enums.rarity import Rarity
from search_builder import SearchBuilder
from search_results import fetch_json

DEFAULT_PACKS_CONFIG = Path(__file__).resolve().parent / "pack_definitions.json"


def _roll(chance: float) -> bool:
    """Return True with the given probability."""
    return random.random() < chance


@dataclass(frozen=True)
class PackSlot:
    """A group of cards in a pack sharing the same rarity requirements.

    Each slot pulls `count` random cards of `rarity`. If `upgrade_rarity` is
    set, every card in the slot has an `upgrade_chance` probability of being
    upgraded to that rarity instead (e.g. the rare slot upgrading to mythic).
    A slot may also be restricted to a card type (e.g. "basic" for the basic
    land slot); slots without a card type exclude basic lands so they do not
    crowd out the dedicated land slot.
    """

    count: int
    rarity: Rarity
    upgrade_rarity: Optional[Rarity] = None
    upgrade_chance: float = 0.0
    card_type: Optional[str] = None

    def roll_rarity(self) -> Rarity:
        if self.upgrade_rarity is not None and _roll(self.upgrade_chance):
            return self.upgrade_rarity
        return self.rarity

    def to_dict(self) -> dict[str, Any]:
        slot: dict[str, Any] = {
            "count": self.count,
            "rarity": self.rarity.value,
        }
        if self.upgrade_rarity is not None:
            slot["upgrade"] = {
                "rarity": self.upgrade_rarity.value,
                "chance": self.upgrade_chance,
            }
        if self.card_type is not None:
            slot["card_type"] = self.card_type
        return slot


@dataclass(frozen=True)
class Pack:
    """A predefined pack type built from an ordered list of slots."""

    name: str
    display_name: str
    slots: tuple[PackSlot, ...]

    @property
    def size(self) -> int:
        return sum(slot.count for slot in self.slots)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "size": self.size,
            "slots": [slot.to_dict() for slot in self.slots],
        }

    def open(self, set_code: str = None, print_cards: bool = False) -> list[dict[str, Any]]:
        """Open the pack: fetch a random card for every slot entry.

        When print_cards is True, the whole pack is resolved before any card
        is sent to the receipt printer, so a failed search cannot leave a
        partially printed pack. Each card then prints using the same print
        path as a single-card search.

        Raises HttpRequestError if a search or print request fails (for
        example, a set code with no cards of the required rarity, or the
        printer API rejecting a job).
        """
        opened = []
        for slot in self.slots:
            for _ in range(slot.count):
                rarity = slot.roll_rarity()
                card_json = _fetch_random_card(
                    rarity=rarity,
                    card_type=slot.card_type,
                    set_code=set_code,
                )
                card = Card.from_json(card_json)
                opened.append((card, _summarize_card(card, card_json, rarity)))

        if print_cards:
            for card, _ in opened:
                card.print()

        return [summary for _, summary in opened]


def _fetch_random_card(rarity: Rarity, card_type: str = None, set_code: str = None) -> dict:
    builder = SearchBuilder()
    builder.add_rarity(rarity)

    if card_type is not None:
        builder.add_card_type(card_type)
    else:
        builder.add_exclude_card_type("basic")

    if set_code is not None:
        builder.add_set_name(set_code)

    return fetch_json(builder.build_url_single_card())


def _summarize_card(card: Card, card_json: dict, slot_rarity: Rarity) -> dict[str, Any]:
    return {
        "name": card.name,
        "rarity": card_json.get("rarity"),
        "slot_rarity": slot_rarity.value,
        "set": card_json.get("set"),
        "set_name": card_json.get("set_name"),
        "type_line": card_json.get("type_line"),
        "mana_cost": card_json.get("mana_cost"),
        "scryfall_uri": card_json.get("scryfall_uri"),
    }


def _parse_rarity(value: Any, pack_name: str) -> Rarity:
    try:
        return Rarity(value)
    except ValueError:
        valid = ", ".join(rarity.value for rarity in Rarity)
        raise ValueError(
            f"Pack {pack_name!r}: unknown rarity {value!r} (expected one of: {valid})"
        ) from None


def _parse_slot(slot_json: Any, pack_name: str) -> PackSlot:
    if not isinstance(slot_json, dict):
        raise ValueError(f"Pack {pack_name!r}: each slot must be a JSON object")

    count = slot_json.get("count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise ValueError(f"Pack {pack_name!r}: slot 'count' must be an integer of at least 1")

    rarity = _parse_rarity(slot_json.get("rarity"), pack_name)

    upgrade_rarity = None
    upgrade_chance = 0.0
    upgrade = slot_json.get("upgrade")
    if upgrade is not None:
        if not isinstance(upgrade, dict):
            raise ValueError(f"Pack {pack_name!r}: slot 'upgrade' must be an object with 'rarity' and 'chance'")
        if "rarity" not in upgrade:
            raise ValueError(f"Pack {pack_name!r}: slot 'upgrade' must include a 'rarity'")
        upgrade_rarity = _parse_rarity(upgrade.get("rarity"), pack_name)
        chance = upgrade.get("chance")
        if not isinstance(chance, (int, float)) or isinstance(chance, bool) or not 0 <= chance <= 1:
            raise ValueError(f"Pack {pack_name!r}: slot upgrade 'chance' must be a number between 0 and 1")
        upgrade_chance = float(chance)

    card_type = slot_json.get("card_type")
    if card_type is not None and (not isinstance(card_type, str) or not card_type.strip()):
        raise ValueError(f"Pack {pack_name!r}: slot 'card_type' must be a non-empty string")

    return PackSlot(
        count=count,
        rarity=rarity,
        upgrade_rarity=upgrade_rarity,
        upgrade_chance=upgrade_chance,
        card_type=card_type,
    )


def _parse_pack(pack_json: Any) -> Pack:
    if not isinstance(pack_json, dict):
        raise ValueError("Each pack definition must be a JSON object")

    name = pack_json.get("name")
    if not name or not isinstance(name, str):
        raise ValueError("Each pack definition must include a non-empty 'name'")

    slots_json = pack_json.get("slots")
    if not isinstance(slots_json, list) or not slots_json:
        raise ValueError(f"Pack {name!r} must include a non-empty 'slots' list")

    return Pack(
        name=name,
        display_name=pack_json.get("display_name") or name,
        slots=tuple(_parse_slot(slot_json, name) for slot_json in slots_json),
    )


def load_packs(config_path: Union[str, Path] = None) -> dict[str, Pack]:
    """Load pack definitions from a JSON config file.

    Resolution order: explicit argument, the PACKS_CONFIG environment
    variable, then the bundled pack_definitions.json. Raises ValueError for a
    missing or invalid config so bad definitions fail at startup rather than
    when a pack is opened.
    """
    load_dotenv()
    if config_path is None:
        config_path = os.getenv("PACKS_CONFIG", "").strip() or DEFAULT_PACKS_CONFIG

    path = Path(config_path)
    if not path.is_file():
        raise ValueError(f"Packs config file not found: {path}")

    try:
        with path.open("r", encoding="utf-8") as file:
            config = json.load(file)
    except json.JSONDecodeError as err:
        raise ValueError(f"Packs config is not valid JSON: {path}") from err

    if not isinstance(config, dict) or not isinstance(config.get("packs"), list):
        raise ValueError("Packs config must be an object with a 'packs' list")

    packs: dict[str, Pack] = {}
    for pack_json in config["packs"]:
        parsed = _parse_pack(pack_json)
        if parsed.name in packs:
            raise ValueError(f"Duplicate pack name in config: {parsed.name!r}")
        packs[parsed.name] = parsed

    if not packs:
        raise ValueError("Packs config must define at least one pack")

    return packs


PACKS: dict[str, Pack] = load_packs()


if __name__ == "__main__":
    for loaded_pack in PACKS.values():
        print(json.dumps(loaded_pack.to_dict(), indent=2))
