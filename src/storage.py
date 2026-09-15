"""
storage.py - Local JSON persistence for HealthBridge.

Responsible for loading/saving app state to a local JSON file.
Never talks to the network. Recovers gracefully from missing or
corrupted files, and skips individual malformed records instead of
losing the whole dataset.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import List, Tuple

try:
    from .models import User, WellnessRecord, ValidationError
except ImportError:  # pragma: no cover - allows `python tests.py` from src/
    from models import User, WellnessRecord, ValidationError

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_FILE = DATA_DIR / "healthbridge_data.json"

EMPTY_STATE = {
    "user": {},
    "records": [],
    "goals": {},
    "onboarded": False,
    "demo_loaded": False,
    "theme": "dark",
}


class Storage:
    """Handles reading and writing the HealthBridge JSON data file."""

    def __init__(self, path: Path = DATA_FILE):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # -- raw load/save ----------------------------------------------------

    def _read_raw(self) -> dict:
        if not self.path.exists():
            return dict(EMPTY_STATE)
        try:
            text = self.path.read_text(encoding="utf-8")
            if not text.strip():
                return dict(EMPTY_STATE)
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("Root JSON element must be an object.")
            return data
        except (json.JSONDecodeError, ValueError, OSError):
            # Corrupted file: back it up so we don't destroy user data,
            # then start fresh rather than crashing.
            try:
                backup = self.path.with_suffix(".corrupted.bak")
                shutil.copy(self.path, backup)
            except OSError:
                pass
            return dict(EMPTY_STATE)

    def _write_raw(self, data: dict) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    # -- high level API -----------------------------------------------------

    def load(self) -> Tuple[User, List[WellnessRecord], bool, bool, str]:
        """Load user, records, onboarded flag, demo_loaded flag, and theme."""
        raw = self._read_raw()

        user_data = raw.get("user") or {}
        try:
            user = User.from_dict(user_data)
        except ValidationError:
            user = User()

        records: List[WellnessRecord] = []
        for entry in raw.get("records", []) or []:
            try:
                records.append(WellnessRecord.from_dict(entry))
            except (ValidationError, KeyError, TypeError):
                # Skip malformed individual entries but keep the rest.
                continue

        onboarded = bool(raw.get("onboarded", False))
        demo_loaded = bool(raw.get("demo_loaded", False))
        theme = raw.get("theme") or "dark"
        if theme not in ("dark", "light", "system"):
            theme = "dark"
        return user, records, onboarded, demo_loaded, theme

    def save(
        self,
        user: User,
        records: List[WellnessRecord],
        onboarded: bool,
        demo_loaded: bool,
        theme: str = "dark",
    ) -> None:
        data = {
            "user": user.to_dict(),
            "records": [r.to_dict() for r in records],
            "onboarded": onboarded,
            "demo_loaded": demo_loaded,
            "theme": theme,
        }
        self._write_raw(data)

    def reset(self) -> None:
        """Delete all stored data (used by 'Reset application data')."""
        self._write_raw(dict(EMPTY_STATE))
