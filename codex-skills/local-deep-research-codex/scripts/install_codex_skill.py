#!/usr/bin/env python3
"""Install this checked-in skill into the active Codex skills directory."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Iterable


IGNORED_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_skill_name(root: Path) -> str:
    skill_md = root / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return root.name
    for line in text.splitlines()[1:40]:
        if line.strip() == "---":
            break
        match = re.match(r"\s*name:\s*[\"']?([^\"'\s#]+)", line)
        if match:
            return match.group(1)
    return root.name


def ignore_generated(_: str, names: Iterable[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        if name in IGNORED_DIRS or Path(name).suffix in IGNORED_SUFFIXES:
            ignored.add(name)
    return ignored


def same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except FileNotFoundError:
        return False


def existing_skill_name(path: Path) -> str | None:
    skill_md = path / "SKILL.md"
    if not skill_md.exists():
        return None
    return read_skill_name(path)


def is_link_like(path: Path) -> bool:
    if path.is_symlink():
        return True
    if sys.platform != "win32":
        return False
    try:
        return bool(path.lstat().st_file_attributes & 0x400)
    except (AttributeError, OSError):
        return False


def emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Copy this Local Deep Research Codex skill into Codex's skills directory.",
    )
    parser.add_argument(
        "--codex-home",
        default=os.environ.get("CODEX_HOME"),
        help="Codex home directory. Defaults to CODEX_HOME or ~/.codex.",
    )
    parser.add_argument(
        "--dest",
        help="Explicit destination skill directory. Defaults to <codex-home>/skills/<skill-name>.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing destination with the same skill name.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned copy operation without writing files.",
    )
    args = parser.parse_args()

    source = skill_root()
    name = read_skill_name(source)
    codex_home = Path(args.codex_home).expanduser() if args.codex_home else Path.home() / ".codex"
    destination = Path(args.dest).expanduser() if args.dest else codex_home / "skills" / name

    if same_path(source, destination):
        emit(
            {
                "ok": True,
                "status": "already-installed",
                "source": str(source),
                "destination": str(destination),
            },
        )
        return 0

    if args.dry_run:
        emit(
            {
                "ok": True,
                "status": "dry-run",
                "source": str(source),
                "destination": str(destination),
                "would_replace": destination.exists(),
                "destination_skill_name": existing_skill_name(destination)
                if destination.exists()
                else None,
            },
        )
        return 0

    replacing_existing = destination.exists()
    if replacing_existing:
        if is_link_like(destination):
            emit(
                {
                    "ok": False,
                    "status": "refused-link-destination",
                    "reason": "destination is a symlink or junction",
                    "source": str(source),
                    "destination": str(destination),
                },
            )
            return 2
        found_name = existing_skill_name(destination)
        if found_name != name:
            emit(
                {
                    "ok": False,
                    "status": "refused-existing-destination",
                    "reason": "destination exists and is not the same skill",
                    "source": str(source),
                    "destination": str(destination),
                    "destination_skill_name": found_name,
                    "source_skill_name": name,
                },
            )
            return 2
        if not args.force:
            emit(
                {
                    "ok": False,
                    "status": "destination-exists",
                    "reason": "rerun with --force to replace this skill",
                    "source": str(source),
                    "destination": str(destination),
                },
            )
            return 2

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, ignore=ignore_generated)
    emit(
        {
            "ok": True,
            "status": "installed",
            "source": str(source),
            "destination": str(destination),
            "replaced_existing": replacing_existing,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
