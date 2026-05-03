"""Helpers for tool argument schemas (LLMs often send Title Case JSON keys)."""

from __future__ import annotations

from typing import Any, Iterable


def normalize_dict_keys(data: Any, field_names: Iterable[str]) -> Any:
    """Map any casing of field names to lowercase canonical keys."""
    allowed = frozenset(field_names)
    if not isinstance(data, dict):
        return data
    out: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(key, str) and key.lower() in allowed:
            out[key.lower()] = value
    return out if out else data
