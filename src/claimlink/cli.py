"""Command-line interface for ClaimLink."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from claimlink import latex, storage
from claimlink.errors import ClaimExportError, ClaimLockError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="claimlink", description="Export ClaimLink claims to LaTeX."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export", help="write a claims.tex file")
    export.add_argument(
        "--input", type=Path, default=storage.project_root() / storage.LOCK_FILENAME
    )
    export.add_argument("--output", type=Path, default=Path("claims.tex"))
    export.set_defaults(handler=_export)
    return parser


def _require_file(path: Path) -> None:
    if not path.is_file():
        reason = "is not a file" if path.exists() else "file not found"
        raise ClaimLockError(f"cannot read {path}: {reason}")


def _same_file(first: Path, second: Path) -> bool:
    """Return whether both paths name the same file, even through links."""
    try:
        return first.samefile(second)
    except OSError:
        return first.resolve() == second.resolve()


def _announce(output: Path) -> None:
    if sys.stdout is None:
        return
    try:
        print(f"Wrote {output}")
        sys.stdout.flush()
    except OSError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        try:
            os.dup2(devnull, sys.stdout.fileno())
        finally:
            os.close(devnull)
    except UnicodeEncodeError:
        pass


def _export(args: argparse.Namespace) -> int:
    _require_file(args.input)
    if _same_file(args.output, args.input):
        raise ClaimExportError(f"refusing to overwrite input file {args.input}")
    text = latex.generate(storage.load(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(text.encode("utf-8"))
    _announce(args.output)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except (ClaimLockError, ClaimExportError, OSError, UnicodeError) as exc:
        print(f"claimlink: error: {exc}", file=sys.stderr)
        return 1
