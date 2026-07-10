"""Persisted 'seen' set so the detector never alerts the same repo twice.

A tiny JSON file of repo full_names. The GitHub Action commits it back after each run,
so tomorrow's digest only contains genuinely new trending repos.
"""

from __future__ import annotations

import json
import os


def load_seen(path: str) -> set[str]:
    """Load the set of already-alerted repo full_names (empty if the file is absent)."""
    if not os.path.exists(path):
        return set()
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return set()
    return set(data.get("seen", []))


def save_seen(path: str, seen: set[str], cap: int = 5000) -> None:
    """Persist the seen set (newest-kept, capped) to JSON, creating parent dirs."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    trimmed = sorted(seen)[:cap]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"seen": trimmed}, fh, indent=2)
