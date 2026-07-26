import unicodedata

from download_card import fetch_card, save_card_json
from printer import _image_url_to_data_url, send_print_job


LINE_WIDTH = 48  # effective chars per line at normal text size


def _canonicalize_string(s: str) -> str:
    """Convert Unicode characters to canonical ASCII forms.
    
    Examples: — (em dash) → -, " → ", " → "
    """
    if not isinstance(s, str):
        return s
    
    # Mapping of Unicode characters to ASCII replacements
    char_map = {
        '−': '-',  # en dash
    }
    
    result = s
    for unicode_char, ascii_replacement in char_map.items():
        result = result.replace(unicode_char, ascii_replacement)
    
    return result


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
        attraction_lights: str = None,
        rotate_image: int = 0,
        color_indicator: str = None,
    ):
        self.name = name
        self.mana_cost = mana_cost
        self.cropped_image = cropped_image
        self.typeline = typeline
        self.oracle_text = oracle_text
        self.flavor_text = flavor_text
        self.counter = counter
        self.attraction_lights = attraction_lights
        self.rotate_image = rotate_image
        self.color_indicator = color_indicator
        
    @classmethod
    def from_json(cls, face_json: dict, fallback: dict = None, face_number: int = 0):
        if not isinstance(face_json, dict):
            raise ValueError("Face JSON must be an object")

        fallback = fallback if isinstance(fallback, dict) else {}

        def value(field_name):
            return face_json.get(field_name, fallback.get(field_name))

        name = value("name")
        if not name:
            raise ValueError("Face JSON must include a non-empty 'name'")
        name = _canonicalize_string(name)

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
            
        lights = value("attraction_lights")
        if lights is not None:
            attraction_lights = "Attraction Lights: " + ", ".join(str(light) for light in lights)
        else:
            attraction_lights = None
            
        layout = value("layout")
        typeline = _canonicalize_string(value("type_line"));
        if layout is not None:
            if layout in ("case", "saga", "class"):
                rotate_image = 90
            elif layout in ("flip"):
                rotate_image = face_number * 180
            elif layout in ("transform"):
                if "Enchantment" in typeline:
                    if any(rotatable_type in typeline for rotatable_type in ("Case", "Saga", "Class")):
                        rotate_image = 90
                    else:
                        rotate_image = 0
                else:
                    rotate_image = 0
            else:
                rotate_image = 0
        else:
            rotate_image = 0
            
        color_indicator = value("color_indicator")
        if color_indicator is not None:
            color_indicator = "{"+"/".join(color_indicator)+"}"
        else:
            color_indicator = None

        return cls(
            name=name,
            mana_cost=_canonicalize_string(value("mana_cost")),
            cropped_image=cropped_image,
            typeline=typeline,
            oracle_text=_canonicalize_string(value("oracle_text")),
            flavor_text=_canonicalize_string(value("flavor_text")),
            counter=_canonicalize_string(counter),
            attraction_lights=attraction_lights,
            rotate_image=rotate_image,
            color_indicator=color_indicator,
        )

    def _build_blocks(self) -> list[dict]:
        def divider():
            blocks.append({"type": "divider", "style": {"double_width": True}})

        typeline_style = {"bold": True, "normal_textsize": True}
        oracle_text_style = {"align": "left", "normal_textsize": True}
        flavor_text_style = {"font": "b", "normal_textsize": True}
        counter_style = {"align": "right", "bold": True, "double_width": True, "double_height": True, "normal_textsize": True}

        blocks = []

        if self.mana_cost:
            mana_len = len(self.mana_cost)
            position = len(self.name) % LINE_WIDTH
            remaining = LINE_WIDTH - position
            # If the mana cost (plus at least one space) fits on the current line,
            # right-align it there; otherwise put it on a new line.
            if remaining >= mana_len + 1:
                padding = remaining - mana_len
                name_line = self.name + " " * padding + self.mana_cost
            else:
                name_line = self.name + "\n" + self.mana_cost.rjust(LINE_WIDTH)
        else:
            name_line = self.name
        blocks.append({"type": "text", "text": name_line, "style": typeline_style})
        if self.cropped_image:
            blocks.append({"type": "image", "image": _image_url_to_data_url(self.cropped_image, self.rotate_image), "center": True})
        if self.typeline:
            divider()
            fullTypeline = self.typeline
            if self.color_indicator is not None:
                fullTypeline = self.color_indicator + " " + fullTypeline
            blocks.append({"type": "text", "text": fullTypeline, "style": typeline_style})
            divider()
        if self.oracle_text:
            blocks.append({"type": "text", "text": self.oracle_text, "style": oracle_text_style})
        if self.attraction_lights:
            blocks.append({"type": "text", "text": self.attraction_lights, "style": oracle_text_style})

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
            faces = [Face.from_json(face_payload, fallback=card_json, face_number=face_payloads.index(face_payload)) for face_payload in face_payloads]
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
    sample_name = "crystal fragments"
    sample_response = fetch_card(sample_name)
    save_card_json(sample_response, sample_name)

    card = Card.from_json(sample_response)
    response = card.print()
    print("Print job response:", response)
