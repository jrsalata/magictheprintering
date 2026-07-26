import json
import os
from pathlib import Path
from typing import Any, Union
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from http_errors import HttpRequestError
import search_builder

MOCK_AANG_PATH = Path(__file__).resolve().parent / "sample_data" / "aang.json"


def _mock_aang_enabled() -> bool:
    raw = os.getenv("SCRYFALL_MOCK_AANG", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def fetch_json(url: str, timeout: int = 10) -> Union[dict[str, Any], list[Any]]:
    """Send a GET request to the given URL and return the parsed JSON body."""
    if _mock_aang_enabled():
        # Temporary outage fallback: return a known local card payload.
        try:
            with MOCK_AANG_PATH.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError) as err:
            raise RuntimeError(f"Failed to load mocked Scryfall response from {MOCK_AANG_PATH}: {err}") from err

    request = Request(
        url,
        method="GET",
        headers={
            "Accept": "application/json",
            "User-Agent": "magictheprintering/1.0",
        },
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)
    except json.JSONDecodeError as err:
        raise RuntimeError("GET response was not valid JSON") from err
    except HTTPError as err:
        details = err.read().decode("utf-8", errors="replace")
        raise HttpRequestError(
            source="search_results",
            status_code=err.code,
            details=details,
            url=url,
        ) from err
    except URLError as err:
        raise RuntimeError(f"Failed to connect to URL: {err.reason}") from err


if __name__ == "__main__":
    search_builder_instance = search_builder.SearchBuilder()
    search_builder_instance.add_color([search_builder.Color.Color.RED, search_builder.Color.Color.GREEN])
    search_builder_instance.add_card_type("creature")
    try:
        result = fetch_json(search_builder_instance.build_url_single_card())
        print(json.dumps(result, indent=2))
    except RuntimeError as err:
        print(f"Error fetching JSON: {err}")