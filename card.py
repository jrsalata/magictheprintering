from download_card import fetch_card, save_card_json
from printer import _image_url_to_data_url, send_print_job


class Face:
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
    def from_json(cls, face_json: dict, fallback: dict = None):
        if not isinstance(face_json, dict):
            raise ValueError("Face JSON must be an object")

        fallback = fallback if isinstance(fallback, dict) else {}

        def value(field_name):
            return face_json.get(field_name, fallback.get(field_name))

        name = value("name")
        if not name:
            raise ValueError("Face JSON must include a non-empty 'name'")

        image_uris = value("image_uris")
        if isinstance(image_uris, dict):
            cropped_image = image_uris.get("art_crop")
        else:
            cropped_image = None

        power = value("power")
        toughness = value("toughness")
        loyalty = value("loyalty")
        defense = value("defense")
        if power is not None and toughness is not None:
            counter = f"{power}/{toughness}"
        elif loyalty is not None:
            counter = loyalty
        elif defense is not None:
            counter = defense
        else:
            counter = None

        return cls(
            name=name,
            mana_cost=value("mana_cost"),
            cropped_image=cropped_image,
            typeline=value("type_line"),
            oracle_text=value("oracle_text"),
            flavor_text=value("flavor_text"),
            counter=counter,
        )

    def _build_blocks(self) -> list[dict]:
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

        return blocks

    def print(self):
        return send_print_job({"blocks": self._build_blocks()})


class Card:
    def __init__(self, faces: list[Face], name: str = None):
        if not faces:
            raise ValueError("Card must contain at least one face")

        self.faces = faces
        self.name = name or faces[0].name

    @classmethod
    def from_json(cls, card_json: dict):
        if not isinstance(card_json, dict):
            raise ValueError("Card JSON must be an object")

        face_payloads = card_json.get("card_faces")
        if isinstance(face_payloads, list) and face_payloads:
            faces = [Face.from_json(face_payload, fallback=card_json) for face_payload in face_payloads]
        else:
            faces = [Face.from_json(card_json)]

        return cls(faces=faces, name=card_json.get("name"))

    def print(self):
        blocks = []
        for index, face in enumerate(self.faces):
            if index > 0:
                blocks.append({"type": "divider", "style": {"double_width": True}})
            blocks.extend(face._build_blocks())

        return send_print_job({"blocks": blocks})


if __name__ == "__main__":
    sample_name = "Invasion of Zendikar"
    sample_response = fetch_card(sample_name)
    save_card_json(sample_response, sample_name)

    card = Card.from_json(sample_response)
    response = card.print()
    print("Print job response:", response)
