"""Read and write the claim lock file."""

from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path

from .errors import ClaimLockError

LOCK_FILENAME = "claim-lock.json"
SCHEMA_VERSION = 1


def project_root() -> Path:
    """Return CLAIMLINK_ROOT if set, otherwise the current directory."""
    root = os.environ.get("CLAIMLINK_ROOT", "").strip()
    if root:
        return Path(root).expanduser().resolve()
    return Path.cwd()


def lock_path(project_root: Path) -> Path:
    """Return the lock file path for a project root."""
    return project_root / LOCK_FILENAME


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    """Build a JSON object, refusing repeated keys instead of dropping data."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ClaimLockError(f"duplicate key {key!r}")
        result[key] = value
    return result


def _reject_json_constant(constant: str) -> object:
    """Refuse NaN/Infinity, which json accepts but RFC 8259 does not."""
    raise ValueError(f"non-finite number {constant} is not valid JSON")


def load(path: Path) -> dict:
    """Return the registry stored at path, or an empty one if it is missing."""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return {"schema_version": SCHEMA_VERSION, "claims": {}}
    except (OSError, UnicodeDecodeError) as exc:
        raise ClaimLockError(f"cannot read {path}: {exc}") from exc
    try:
        registry = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except ClaimLockError as exc:
        raise ClaimLockError(f"cannot read {path}: {exc}") from exc
    except (OSError, ValueError, RecursionError) as exc:
        # Covers JSONDecodeError, huge integers (3.11+) and deep nesting.
        raise ClaimLockError(f"cannot read {path}: {exc}") from exc

    if not isinstance(registry, dict):
        raise ClaimLockError(f"{path}: top level must be a JSON object")
    claims = registry.get("claims", {})
    if not isinstance(claims, dict):
        raise ClaimLockError(f"{path}: 'claims' must be a JSON object")
    for name, record in claims.items():
        if not isinstance(name, str):
            raise ClaimLockError(f"{path}: claim names must be strings, got {name!r}")
        if not isinstance(record, dict):
            raise ClaimLockError(f"{path}: claim {name!r} must be a JSON object")

    registry["claims"] = claims
    registry.setdefault("schema_version", SCHEMA_VERSION)
    return registry


def save(path: Path, registry: dict) -> None:
    """Write the registry atomically, with claim names sorted."""
    claims = registry.get("claims", {})
    payload = {**registry, "claims": dict(sorted(claims.items()))}
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
