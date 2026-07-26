import random
from dataclasses import dataclass
from typing import Any, Optional

from card import Card
from enums.rarity import Rarity
from search_builder import SearchBuilder
from search_results import fetch_json


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

        When print_cards is True, each card is sent to the receipt printer as
        it is opened, using the same print path as a single-card search.

        Raises HttpRequestError if a search or print request fails (for
        example, a set code with no cards of the required rarity, or the
        printer API rejecting a job mid-pack).
        """
        cards = []
        for slot in self.slots:
            for _ in range(slot.count):
                rarity = slot.roll_rarity()
                card_json = _fetch_random_card(
                    rarity=rarity,
                    card_type=slot.card_type,
                    set_code=set_code,
                )
                card = Card.from_json(card_json)
                if print_cards:
                    card.print()
                cards.append(_summarize_card(card, card_json, rarity))
        return cards


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


DRAFT_BOOSTER = Pack(
    name="draft_booster",
    display_name="Draft Booster",
    slots=(
        PackSlot(count=10, rarity=Rarity.COMMON),
        PackSlot(count=3, rarity=Rarity.UNCOMMON),
        PackSlot(
            count=1,
            rarity=Rarity.RARE,
            upgrade_rarity=Rarity.MYTHIC,
            upgrade_chance=1 / 8,
        ),
        PackSlot(count=1, rarity=Rarity.COMMON, card_type="basic"),
    ),
)

MINI_PACK = Pack(
    name="mini_pack",
    display_name="Mini Pack",
    slots=(
        PackSlot(count=3, rarity=Rarity.COMMON),
        PackSlot(count=1, rarity=Rarity.UNCOMMON),
        PackSlot(
            count=1,
            rarity=Rarity.RARE,
            upgrade_rarity=Rarity.MYTHIC,
            upgrade_chance=1 / 8,
        ),
    ),
)

PACKS: dict[str, Pack] = {
    pack.name: pack
    for pack in (
        DRAFT_BOOSTER,
        MINI_PACK,
    )
}


if __name__ == "__main__":
    import json

    for pack in PACKS.values():
        print(json.dumps(pack.to_dict(), indent=2))
