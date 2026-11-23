"""Normalization and deterministic comparison of claim values."""

import json
import math


def normalize(value: object) -> object:
    """Convert a supported value into plain JSON-compatible data."""
    try:
        return _normalize(value, set())
    except RecursionError:
        raise ValueError("claim value is nested too deeply") from None


def _plain_str(text: str) -> str:
    """Return an exact str, rejecting unpaired surrogates."""
    text = str.__str__(text)
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("claim string is not valid UTF-8 (unpaired surrogate)") from None
    return text


def _normalize(value: object, active: set) -> object:
    if value is None or isinstance(value, bool):
        return value

    # numpy scalars are not guaranteed to be JSON-serializable even when they
    # subclass int/float, so convert them before the native checks.
    if type(value).__module__ == "numpy":
        if getattr(value, "ndim", 0) == 0 and hasattr(value, "item"):
            return _normalize(value.item(), active)
        raise TypeError(
            "unsupported claim value type: "
            f"{type(value).__name__}; only scalar numpy values are supported"
        )

    # Use the base-class hooks so subclass overrides cannot change the value.
    if isinstance(value, int):
        return int.__int__(value)

    if isinstance(value, float):
        number = float.__float__(value)
        if not math.isfinite(number):
            raise ValueError(
                f"non-finite float {number!r} is not a valid JSON number"
            )
        return number

    if isinstance(value, str):
        return _plain_str(value)

    if isinstance(value, list):
        if id(value) in active:
            raise ValueError("claim value contains a circular reference")
        active.add(id(value))
        try:
            return [_normalize(item, active) for item in value]
        finally:
            active.discard(id(value))

    if isinstance(value, dict):
        if id(value) in active:
            raise ValueError("claim value contains a circular reference")
        active.add(id(value))
        try:
            normalized = {}
            for key, item in value.items():
                if not isinstance(key, str):
                    raise TypeError(
                        "claim dictionaries need string keys, "
                        f"got {type(key).__name__}"
                    )
                # exact str keys keep canonical sorting off subclass __lt__
                normalized[_plain_str(key)] = _normalize(item, active)
            return normalized
        finally:
            active.discard(id(value))

    raise TypeError(f"unsupported claim value type: {type(value).__name__}")


def value_type(value: object) -> str:
    """Return the ClaimLink type name of an already-normalized value."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    raise TypeError(f"unsupported claim value type: {type(value).__name__}")


def canonical(value: object) -> str:
    """Return a deterministic JSON string for an already-normalized value."""
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
