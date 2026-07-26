import json
import os
from pathlib import Path
from typing import Any

MOCK_AANG_PATH = Path(__file__).resolve().parent / "sample_data" / "aang.json"


def _mock_aang_enabled() -> bool:
    raw = os.getenv("SCRYFALL_MOCK_AANG", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def load_mock_aang_card() -> dict[str, Any]:
    try:
        with MOCK_AANG_PATH.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError) as err:
        raise RuntimeError(f"Failed to load mocked Scryfall response from {MOCK_AANG_PATH}: {err}") from err
