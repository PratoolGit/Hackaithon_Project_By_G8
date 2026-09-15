"""
app.py - Application controller for HealthBridge.

Sits between storage.py (persistence) and ui.py (PySide6 views).
The UI never touches the JSON file or business rules directly -
it only calls methods on HealthBridgeApp.
"""
from typing import List, Optional
try:
    from .models import User, WellnessRecord, ValidationError
    from .storage import Storage
    from .analytics import WellnessReport
    from .sample_data import generate_demo_records
except ImportError:  # pragma: no cover - allows `python tests.py` from src/
    from models import User, WellnessRecord, ValidationError
    from storage import Storage
    from analytics import WellnessReport
    from sample_data import generate_demo_records

class HealthBridgeApp:
    """Central controller holding app state and exposing safe operations."""

    def __init__(self, storage: Optional[Storage] = None):
        self.storage = storage or Storage()
        (
            self.user,
            self.records,
            self.onboarded,
            self.demo_loaded,
            self.theme,
        ) = self.storage.load()

    # -- persistence helpers ------------------------------------------------

    def _save(self) -> None:
        self.storage.save(
            self.user, self.records, self.onboarded, self.demo_loaded, self.theme
        )

    # -- onboarding / profile -------------------------------------------------

    def complete_onboarding(self, name: str, age, goals: dict) -> None:
        user = User(name=name, age=age or None, goals=goals or {})
        self.user = user
        self.onboarded = True
        self._save()

    def update_profile(self, name: str, age) -> None:
        self.user.name = User.validate_name(name)
        self.user.age = User.validate_age(age) if age not in (None, "") else None
        self._save()

    def update_goals(self, goals: dict) -> None:
        for key, value in goals.items():
            self.user.set_goal(key, value)
        self._save()

    def set_theme(self, theme: str) -> None:
        """Persist the chosen appearance mode ('dark', 'light', or 'system')."""
        theme = (theme or "dark").lower()
        if theme not in ("dark", "light", "system"):
            theme = "dark"
        self.theme = theme
        self._save()

    # -- records -----------------------------------------------------------

    def find_record(self, date: str) -> Optional[WellnessRecord]:
        for r in self.records:
            if r.date == date:
                return r
        return None

    def add_or_update_record(
        self, date, sleep_hours, activity_minutes, hydration_liters, wellness_minutes
    ) -> WellnessRecord:
        record = WellnessRecord(
            date=date,
            sleep_hours=sleep_hours,
            activity_minutes=activity_minutes,
            hydration_liters=hydration_liters,
            wellness_minutes=wellness_minutes,
            is_demo=False,
        )
        existing = self.find_record(record.date)
        if existing:
            self.records.remove(existing)
        self.records.append(record)
        self._save()
        return record

    def delete_record(self, date: str) -> bool:
        existing = self.find_record(date)
        if not existing:
            return False
        self.records.remove(existing)
        self._save()
        return True

    def sorted_records(self) -> List[WellnessRecord]:
        return sorted(self.records, key=lambda r: r.date_obj, reverse=True)

    # -- demo data -----------------------------------------------------------

    def load_demo_data(self) -> None:
        existing_dates = {r.date for r in self.records}
        demo_records = [r for r in generate_demo_records(10) if r.date not in existing_dates]
        self.records.extend(demo_records)
        self.demo_loaded = True
        self._save()

    def clear_demo_data(self) -> None:
        self.records = [r for r in self.records if not r.is_demo]
        self.demo_loaded = False
        self._save()

    def reset_all(self) -> None:
        self.storage.reset()
        (
            self.user,
            self.records,
            self.onboarded,
            self.demo_loaded,
            self.theme,
        ) = self.storage.load()

    # -- analytics -----------------------------------------------------------

    @property
    def report(self) -> WellnessReport:
        return WellnessReport(self.user, self.records)
