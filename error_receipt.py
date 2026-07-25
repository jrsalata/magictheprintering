from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from http_errors import HttpRequestError


TEMPLATE_DIR = Path(__file__).resolve().parent / "error_templates"
PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def _candidate_templates(err: HttpRequestError) -> list[Path]:
    candidates: list[Path] = []
    status = err.status_code

    candidates.append(TEMPLATE_DIR / "http" / f"{status}.json")
    candidates.append(TEMPLATE_DIR / "http" / f"{status // 100}xx.json")
    candidates.append(TEMPLATE_DIR / "http" / "default.json")
    candidates.append(TEMPLATE_DIR / "default.json")

    return candidates


def _load_template(err: HttpRequestError) -> dict[str, Any]:
    for path in _candidate_templates(err):
        if path.exists():
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)

    return {
        "blocks": [
            {"type": "text", "text": "HTTP error"},
            {"type": "text", "text": "{{source}} status {{status}}"},
            {"type": "text", "text": "{{details}}"},
        ]
    }


def _replace_placeholders(text: str, context: dict[str, str]) -> str:
    def replacer(match: re.Match[str]) -> str:
        key = match.group(1)
        return context.get(key, "")

    return PLACEHOLDER_PATTERN.sub(replacer, text)


def _render(node: Any, context: dict[str, str]) -> Any:
    if isinstance(node, str):
        return _replace_placeholders(node, context)
    if isinstance(node, list):
        return [_render(item, context) for item in node]
    if isinstance(node, dict):
        rendered: dict[str, Any] = {}
        for key, value in node.items():
            rendered[key] = _render(value, context)
        return rendered
    return node


def build_http_error_receipt(err: HttpRequestError) -> dict[str, Any]:
    """Build a printable block payload from JSON templates for an HTTP error."""
    template = deepcopy(_load_template(err))
    context = err.to_context()
    context["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

    rendered = _render(template, context)
    if not isinstance(rendered, dict) or "blocks" not in rendered:
        raise ValueError("Error template must be an object with a 'blocks' field")
    return rendered