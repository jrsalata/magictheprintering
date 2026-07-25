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

    def print(self):
        blocks = []

        if self.name:
            blocks.append({"type": "text", "text": self.name})
        if self.mana_cost:
            blocks.append({"type": "text", "text": self.mana_cost})
        if self.cropped_image:
            blocks.append({"type": "image", "image": _image_url_to_data_url(self.cropped_image)})
        if self.typeline:
            blocks.append({"type": "text", "text": self.typeline})
        if self.oracle_text:
            blocks.append({"type": "text", "text": self.oracle_text})
        if self.flavor_text:
            blocks.append({"type": "text", "text": self.flavor_text})
        if self.counter:
            blocks.append({"type": "text", "text": self.counter})

        return send_print_job({"blocks": blocks})


if __name__ == "__main__":
    card = Card(
        name="Aang, Air Nomad",
        mana_cost="{3}{W}{W}",
        cropped_image="https://cards.scryfall.io/art_crop/front/f/3/f369827d-e4cd-4bc7-8c5e-72882eff0908.jpg?1783904788",
        typeline="Legendary Creature — Human Avatar Ally",
        oracle_text="Flying (This creature can't be blocked except by creatures with flying or reach.)\nVigilance (Attacking doesn't cause this creature to tap.)\nOther creatures you control have vigilance.",
        flavor_text="Monk Gyatso taught Aang many things, most importantly to live with joy.",
    )
    response = card.print()
    print("Print job response:", response)
