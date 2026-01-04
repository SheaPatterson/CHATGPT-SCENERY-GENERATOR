"""Shared helpers for filesystem and naming tasks."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable


def slugify(value: str) -> str:
    """Return a filesystem-friendly slug."""
    cleaned = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in value)
    return "_".join(filter(None, cleaned.split("_"))) or "UNKNOWN"


def dated_bulk_name(prefix: str = "BULK") -> str:
    stamp = datetime.now().strftime("%Y%m%d")
    return f"{prefix}_{stamp}.zip"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def ensure_unique_paths(paths: Iterable[Path]) -> None:
    seen: set[Path] = set()
    for path in paths:
        if path in seen:
            raise ValueError(f"Duplicate output path detected: {path}")
        seen.add(path)
