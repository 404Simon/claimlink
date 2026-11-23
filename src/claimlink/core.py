"""Register scientific claims in the project's claim-lock.json file."""

from __future__ import annotations

import json
import warnings
from datetime import datetime, timezone

from . import location, serialization, storage
from .errors import (
    ClaimLocationChangedWarning,
    ClaimLocationUnavailableWarning,
    ClaimValueChangedWarning,
)


def claim(
    name: str,
    value: object,
    *,
    unit: str | None = None,
    description: str | None = None,
) -> None:
    """Record a claim, warning about changed values or locations."""
    if not isinstance(name, str):
        raise TypeError(f"claim name must be a string, got {type(name).__name__}")
    if not name.strip():
        raise ValueError("claim name must not be empty")
    for label, argument in (("unit", unit), ("description", description)):
        if argument is not None and not isinstance(argument, str):
            raise TypeError(
                f"claim {label} must be a string or None, "
                f"got {type(argument).__name__}"
            )
    for label, text in (("name", name), ("unit", unit), ("description", description)):
        if text is not None:
            try:
                text.encode("utf-8")
            except UnicodeEncodeError:
                raise ValueError(
                    f"claim {label} is not valid UTF-8 (unpaired surrogate)"
                ) from None

    normalized = serialization.normalize(value)
    vtype = serialization.value_type(normalized)

    root = storage.project_root()
    path = storage.lock_path(root)
    registry = storage.load(path)
    current, unavailable = location.detect_location(root)
    for message in unavailable:
        warnings.warn(
            f"Claim {name!r}: {message}.",
            ClaimLocationUnavailableWarning,
            stacklevel=2,
        )

    now = _now()
    claims = registry.setdefault("claims", {})
    existing = claims.get(name)
    if existing is None:
        record = {
            "name": name,
            "value": normalized,
            "value_type": vtype,
            "unit": unit,
            "description": description,
            "location": current,
            "created_at": now,
            "updated_at": now,
        }
    else:
        previous = existing.get("value")
        if serialization.canonical(previous) != serialization.canonical(normalized):
            warnings.warn(
                f"Claim {name!r} changed:\n"
                f"  Previous value: {json.dumps(previous, ensure_ascii=False)}\n"
                f"  New value:      {json.dumps(normalized, ensure_ascii=False)}\n\n"
                "The claim-lock.json file has been updated.",
                ClaimValueChangedWarning,
                stacklevel=2,
            )
        canonical = existing.get("location")
        if not isinstance(canonical, dict) or canonical.get("type") not in (
            "script",
            "notebook",
        ):
            canonical = current
        elif _identity(canonical) != _identity(current):
            warnings.warn(
                f"Claim {name!r} was declared from a different location:\n"
                f"  Canonical location: {_describe(canonical)}\n"
                f"  Current location:   {_describe(current)}\n"
                "The canonical location was kept.",
                ClaimLocationChangedWarning,
                stacklevel=2,
            )
        record = {
            **existing,
            "name": name,
            "value": normalized,
            "location": canonical,
            "value_type": vtype,
            "unit": unit,
            "description": description,
            "created_at": existing.get("created_at") or now,
            "updated_at": now,
        }
    claims[name] = record
    storage.save(path, registry)


def _now() -> str:
    """Return the current UTC timestamp in the lock file format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _identity(loc: dict) -> tuple:
    """Return the fields that identify a canonical location."""
    return (loc.get("type"), loc.get("file"), loc.get("cell_id"), loc.get("line"))


def _describe(loc: dict) -> str:
    """Return a one-line description of a source location."""
    where = f"{loc.get('type')} {loc.get('file')}"
    if loc.get("cell_id") is not None:
        where += f" cell {loc['cell_id']}"
    return f"{where} line {loc.get('line')}"
