import os
from dotenv import load_dotenv
from urllib.parse import quote
import enums.color as Color
import enums.comparison as Comparison
import enums.typeline as TypeLine
class SearchBuilder:
    STATIC_TEXT = "unique:cards -has:flavor_name game:paper -is:extra"
    raw_query = STATIC_TEXT
    def __init__(self):
        load_dotenv()
        self.search_url = os.getenv("SEARCH_URL", "").strip()

        if not self.search_url:
            raise ValueError("Missing required environment variable: SEARCH_URL")

    def add_card_type(self, card_type: str) -> None:
        self.raw_query += f" t:{card_type}"

    def add_mana_value(self, value: int, comparison: Comparison.Comparison = Comparison.Comparison.EQUAL) -> None:
        self.raw_query += f" mv{comparison.value}{value}"

    def add_color(self, colors: list[Color.Color]) -> None:
        self.raw_query += f" c:{''.join(color.value for color in colors)}"

    def add_type_line(self, type_line: TypeLine.TypeLine) -> None:
        self.raw_query += f" t:{type_line.value}"

    def add_commander_legality(self) -> None:
        self.raw_query += " f:commander"

    def add_exclude_lands(self) -> None:
        self.raw_query += " -type:land"

    def build_search_query(self) -> str:
        return self.raw_query

    def build_url(self) -> str:
        encoded_query = quote(self.raw_query, safe="")
        return f"{self.search_url.rstrip('/')}/cards/search?q={encoded_query}"

    def build_url_single_card(self) -> str:
        encoded_query = quote(self.raw_query, safe="")
        return f"{self.search_url.rstrip('/')}/cards/random?q={encoded_query}"

    def reset_query(self) -> None:
        self.raw_query = self.STATIC_TEXT

if __name__ == "__main__":
    builder = SearchBuilder()
    builder.add_card_type("creature")
    builder.add_mana_value(3, Comparison.Comparison.GREATER_THAN)
    builder.add_color([Color.Color.RED, Color.Color.GREEN])
    builder.add_type_line(TypeLine.TypeLine.CREATURE)
    builder.add_commander_legality()
    print(builder.build_search_query())
    print(builder.build_url())
    print(builder.build_url_single_card())