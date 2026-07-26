import argparse
import json
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from http_errors import HttpRequestError
from scryfall_mock import _mock_aang_enabled, load_mock_aang_card

SCRYFALL_FUZZY_URL = "https://api.scryfall.com/cards/named?fuzzy="


def sanitize_filename(card_name: str) -> str:
    sanitized = re.sub(r"[\\/:*?\"<>|]", "", card_name).strip().lower()
    return sanitized or "card"


def fetch_card(card_name: str) -> dict:
    if _mock_aang_enabled():
        # Temporary outage fallback: return a known local card payload.
        return load_mock_aang_card()

    url = f"{SCRYFALL_FUZZY_URL}{quote(card_name)}"
    request = Request(
        url,
        headers={
            "User-Agent": "magictheprintering/1.0",
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as err:
        try:
            payload = json.load(err)
            details = payload.get("details")
        except (json.JSONDecodeError, ValueError):
            details = None
        message = details or f"HTTP error {err.code}"
        raise HttpRequestError(
            source="scryfall",
            status_code=err.code,
            details=message,
            url=url,
        ) from err
    except URLError as err:
        raise RuntimeError(f"Network error while calling Scryfall: {err.reason}") from err


def save_card_json(card_data: dict, original_name: str) -> Path:
    base_dir = Path(__file__).resolve().parent
    output_dir = base_dir / "sample_data"
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{sanitize_filename(original_name)}.json"
    output_path = output_dir / filename

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(card_data, file, indent=2, ensure_ascii=False)
        file.write("\n")

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download a Magic card JSON from Scryfall (fuzzy name lookup)."
    )
    parser.add_argument("card_name", help="Card name to search (example: Lightning Bolt)")
    args = parser.parse_args()

    card_name = args.card_name.strip()
    if not card_name:
        raise SystemExit("Card name cannot be empty.")

    card_data = fetch_card(card_name)
    saved_path = save_card_json(card_data, card_name)
    print(f"Saved card JSON to: {saved_path}")


if __name__ == "__main__":
    main()