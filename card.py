import json
import os

from printer import _image_url_to_data_url, send_print_job


class Card:
    def __init__(
        self,
        name: str,
        mana_cost: str = None,
        cropped_image: str = None,
        typeline: str = None,
        oracle_text: str = None,
        flavor_text: str = None,
        counter: str = None,
    ):
        self.name = name
        self.mana_cost = mana_cost
        self.cropped_image = cropped_image
        self.typeline = typeline
        self.oracle_text = oracle_text
        self.flavor_text = flavor_text
        self.counter = counter

    @classmethod
    def from_json(cls, card_json: dict):
        name = card_json.get("name")
        if not name:
            raise ValueError("Card JSON must include a non-empty 'name'")

        image_uris = card_json.get("image_uris")
        if isinstance(image_uris, dict):
            cropped_image = image_uris.get("art_crop")
        else:
            cropped_image = None

        power = card_json.get("power")
        toughness = card_json.get("toughness")
        if power is not None and toughness is not None:
            counter = f"{power}/{toughness}"
        else:
            counter = None

        return cls(
            name=name,
            mana_cost=card_json.get("mana_cost"),
            cropped_image=cropped_image,
            typeline=card_json.get("type_line"),
            oracle_text=card_json.get("oracle_text"),
            flavor_text=card_json.get("flavor_text"),
            counter=counter,
        )

    def print(self):
        def divider():
            blocks.append({"type": "divider", "style": {"double_width": True}})

        typeline_style = {"bold": True, "normal_textsize": True}
        oracle_text_style = {"align": "left", "normal_textsize": True}
        flavor_text_style = {"font": "b", "normal_textsize": True}
        counter_style = {"align": "right", "bold": True, "double_width": True, "double_height": True, "normal_textsize": True}

        LINE_WIDTH = 48  # effective chars per line at normal text size

        blocks = []

        name_line = f"{self.name:<{LINE_WIDTH - len(self.mana_cost)}}{self.mana_cost}" if self.mana_cost else self.name
        blocks.append({"type": "text", "text": name_line, "style": typeline_style})
        if self.cropped_image:
            blocks.append({"type": "image", "image": _image_url_to_data_url(self.cropped_image), "center": True})
        if self.typeline:
            divider()
            blocks.append({"type": "text", "text": self.typeline, "style": typeline_style})
            divider()
        if self.oracle_text:
            blocks.append({"type": "text", "text": self.oracle_text, "style": oracle_text_style})
        if self.flavor_text:
            divider()
            blocks.append({"type": "text", "text": self.flavor_text, "style": flavor_text_style})
        if self.counter:
            blocks.append({"type": "text", "text": self.counter, "style": counter_style})

        return send_print_job({"blocks": blocks})


if __name__ == "__main__":
    sample_path = os.path.join(os.path.dirname(__file__), "sample_data", "aang.json")
    with open(sample_path, "r", encoding="utf-8") as file:
        sample_response = json.load(file)

    card = Card.from_json(sample_response)
    response = card.print()
    print("Print job response:", response)
