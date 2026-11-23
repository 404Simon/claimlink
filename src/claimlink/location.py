"""Detect the source location where a claim was declared."""

import builtins
import hashlib
import os
import sys
from pathlib import Path


def _format_path(path: Path, project_root: Path) -> str:
    """Return path relative to project_root if inside it, else absolute POSIX."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _execution_count(shell) -> int | None:
    """Return the In[n] count of the executing cell."""
    prompt_count = getattr(getattr(shell, "displayhook", None), "prompt_count", None)
    if isinstance(prompt_count, int) and not isinstance(prompt_count, bool):
        return prompt_count
    # No arithmetic fallback: IPython 9.8 moved the execution_count increment
    # before the cell body (9.7 still increments at the end), so the counter is
    # not the In[n] of the running cell; only displayhook.prompt_count (set by
    # run_cell) is trusted.
    return None


def detect_location(project_root: Path) -> tuple[dict, list[str]]:
    """Return the declaration location and messages for fields that are unavailable."""
    package_dir = Path(__file__).resolve().parent
    frame = sys._getframe()
    while frame is not None:
        try:
            in_package = Path(frame.f_code.co_filename).resolve().is_relative_to(package_dir)
        except (OSError, ValueError, RuntimeError):
            in_package = False
        if not in_package:
            break
        frame = frame.f_back

    # shortcut: magic frames report body-relative lines (%%time, %%capture) or line 1 (%time); upgrade if exact magic-aware mapping is needed.
    line = frame.f_lineno if frame is not None else 0
    filename = frame.f_code.co_filename if frame is not None else None
    unavailable: list[str] = []

    if filename is not None:
        try:
            is_file = Path(filename).is_file()
        except (OSError, ValueError, RuntimeError):
            is_file = False
        if is_file:
            try:
                path = _format_path(Path(filename), project_root)
            except (OSError, ValueError, RuntimeError):
                path = None
            if path is not None:
                return {"type": "script", "file": path, "line": line}, unavailable

    get_ipython = getattr(builtins, "get_ipython", None)
    shell = None
    if callable(get_ipython):
        try:
            shell = get_ipython()
        except Exception:
            shell = None

    if shell is not None:
        user_ns = getattr(shell, "user_ns", None)
        if not isinstance(user_ns, dict):
            user_ns = {}

        raw_file = (
            user_ns.get("__session__")
            or user_ns.get("__vsc_ipynb_file__")
            or os.environ.get("JPY_SESSION_NAME")
        )
        notebook_file = None
        if raw_file is not None:
            try:
                notebook_file = _format_path(Path(raw_file).expanduser(), project_root)
            except (OSError, TypeError, ValueError, RuntimeError):
                notebook_file = None
        if notebook_file is None:
            unavailable.append("notebook filename is not available from this frontend")

        parent_header = getattr(shell, "parent_header", None)
        if not isinstance(parent_header, dict):
            parent_header = {}

        metadata = parent_header.get("metadata")
        cell_id = metadata.get("cellId") if isinstance(metadata, dict) else None
        if not isinstance(cell_id, str) or not cell_id:
            cell_id = None
            unavailable.append("notebook cell id is not available from this frontend")

        execution_count = _execution_count(shell)

        content = parent_header.get("content")
        code = content.get("code") if isinstance(content, dict) else None
        cell_source_hash = (
            hashlib.sha256(code.encode("utf-8")).hexdigest()
            if isinstance(code, str) and code
            else None
        )

        # Silent runs have no In[n] label; jupyter_client still sends
        # store_history=True, so both flags are checked. Cell id and hash stay valid.
        if isinstance(content, dict) and (
            content.get("store_history") is False or content.get("silent") is True
        ):
            execution_count = None

        # The last compiled key is the current cell, unless a nested run_cell was
        # cached after it; then the executing cell is the key mapped to this count.
        # Pseudo filenames are absent from the map, so those stay best effort.
        # shortcut: silent/no-history cells reuse the next execution number, so their cell fields can be misattributed; upgrade if %run-of-notebook provenance matters.
        filename_map = getattr(getattr(shell, "compile", None), "_filename_map", None)
        if isinstance(filename_map, dict) and isinstance(filename, str):
            current = next(reversed(filename_map), None)
            if filename in filename_map and filename != current:
                # A nested run_cell caches after the executing cell, so the
                # executing key need not be last; its mapped number still matches.
                if not (
                    filename_map[filename] == execution_count
                    and filename_map[current] != execution_count
                ):
                    cell_id = execution_count = cell_source_hash = None
                    unavailable.append(
                        "claim is declared in a different notebook cell than the executing cell"
                    )

        return (
            {
                "type": "notebook",
                "file": notebook_file,
                "cell_id": cell_id,
                "execution_count": execution_count,
                "line": line,
                "cell_source_hash": cell_source_hash,
            },
            unavailable,
        )

    unavailable.append("source file is not available")
    return {"type": "script", "file": None, "line": line}, unavailable
