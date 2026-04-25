"""Utility helpers shared across the backend."""


def to_camel(snake_str: str) -> str:
    """Convert a snake_case string to camelCase."""
    parts = snake_str.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def snake_dict_to_camel(d: dict) -> dict:
    """Recursively convert all dict keys from snake_case to camelCase.

    Firestore stores timestamps as datetime objects; we convert them to
    ISO-8601 strings so the JSON response is frontend-compatible.
    """
    from datetime import datetime

    out = {}
    for k, v in d.items():
        camel_key = to_camel(k)
        if isinstance(v, dict):
            out[camel_key] = snake_dict_to_camel(v)
        elif isinstance(v, list):
            out[camel_key] = [
                snake_dict_to_camel(i) if isinstance(i, dict) else i for i in v
            ]
        elif isinstance(v, datetime):
            out[camel_key] = v.isoformat()
        else:
            out[camel_key] = v
    return out
