"""
models.py - Core OOP data models for HealthBridge.

Contains the User and WellnessRecord classes. These classes are
intentionally UI-agnostic: they only validate and hold data.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional


class ValidationError(Exception):
    """Raised when a model fails validation with a friendly message."""


# ---------------------------------------------------------------------------
# Goals / targets
# ---------------------------------------------------------------------------

DEFAULT_GOALS = {
    "sleep_hours": 8.0,
    "activity_minutes": 30.0,
    "hydration_liters": 2.0,
    "wellness_minutes": 15.0,
}

# Reasonable bounds used for friendly validation messages.
LIMITS = {
    "sleep_hours": (0, 24),
    "activity_minutes": (0, 1440),
    "hydration_liters": (0, 20),
    "wellness_minutes": (0, 1440),
}


def validate_goal_value(name: str, value: float) -> float:
    """Validate a single goal/target value. Raises ValidationError."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"Please enter a valid number for {name.replace('_', ' ')}.")
    if value <= 0:
        raise ValidationError(f"Your {name.replace('_', ' ')} target must be greater than zero.")
    low, high = LIMITS.get(name, (0, 10_000))
    if value > high:
        raise ValidationError(
            f"That {name.replace('_', ' ')} target looks unrealistic. "
            f"Please enter a value up to {high}."
        )
    return value


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

@dataclass
class User:
    """Represents the local app user (single-user, offline)."""

    name: str = "Friend"
    age: Optional[int] = None
    user_id: str = "local-user"
    goals: dict = field(default_factory=lambda: dict(DEFAULT_GOALS))

    def __post_init__(self):
        self.name = self.validate_name(self.name)
        if self.age is not None:
            self.age = self.validate_age(self.age)
        # Ensure all goal keys exist, fall back to defaults if missing.
        merged = dict(DEFAULT_GOALS)
        merged.update(self.goals or {})
        self.goals = {k: validate_goal_value(k, v) for k, v in merged.items()}

    @staticmethod
    def validate_name(name: str) -> str:
        if name is None or not str(name).strip():
            raise ValidationError("Please enter your name so we can greet you properly.")
        name = str(name).strip()
        if len(name) > 40:
            raise ValidationError("Please use a shorter name (under 40 characters).")
        return name

    @staticmethod
    def validate_age(age) -> int:
        try:
            age = int(age)
        except (TypeError, ValueError):
            raise ValidationError("Please enter a valid whole number for age.")
        if age < 5 or age > 120:
            raise ValidationError("Please enter an age between 5 and 120.")
        return age

    def set_goal(self, name: str, value: float) -> None:
        self.goals[name] = validate_goal_value(name, value)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "age": self.age,
            "user_id": self.user_id,
            "goals": self.goals,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        if not data:
            return cls()
        return cls(
            name=data.get("name", "Friend"),
            age=data.get("age"),
            user_id=data.get("user_id", "local-user"),
            goals=data.get("goals", {}),
        )


# ---------------------------------------------------------------------------
# WellnessRecord
# ---------------------------------------------------------------------------

DATE_FORMAT = "%Y-%m-%d"


@dataclass
class WellnessRecord:
    """One day's worth of wellness tracking data."""

    date: str  # YYYY-MM-DD
    sleep_hours: float
    activity_minutes: float
    hydration_liters: float
    wellness_minutes: float
    is_demo: bool = False

    def __post_init__(self):
        self.date = self.validate_date(self.date)

        self.sleep_hours = self._validate_number(
            "sleep_hours",
            self.sleep_hours,
            0,
            24,
        )

        self.activity_minutes = self._validate_number(
            "activity_minutes",
            self.activity_minutes,
            0,
            1440,
        )

        self.hydration_liters = self._validate_number(
            "hydration_liters",
            self.hydration_liters,
            0,
            20,
        )

        self.wellness_minutes = self._validate_number(
            "wellness_minutes",
            self.wellness_minutes,
            0,
            1440,
        )

        self._validate_daily_balance()

    def _validate_daily_balance(self):
        """
        Validate relationships between daily wellness metrics.

        A day contains 1,440 minutes. Sleep, activity and wellness
        therefore cannot independently consume unlimited time.
        """

        total_minutes = 24 * 60

        sleep_minutes = self.sleep_hours * 60

        awake_minutes = total_minutes - sleep_minutes

        # --------------------------------------------------------
        # Activity cannot exceed the person's available awake time
        # --------------------------------------------------------

        if self.activity_minutes > awake_minutes:
            raise ValidationError(
                f"This record is not realistic: you entered "
                f"{self.sleep_hours:.1f} hours of sleep, leaving only "
                f"{awake_minutes:.0f} minutes of awake time, but "
                f"{self.activity_minutes:.0f} minutes of activity."
            )

        # --------------------------------------------------------
        # Wellness time also cannot exceed available awake time
        # --------------------------------------------------------

        if self.wellness_minutes > awake_minutes:
            raise ValidationError(
                f"This record is not realistic: you entered "
                f"{self.sleep_hours:.1f} hours of sleep, leaving only "
                f"{awake_minutes:.0f} minutes of awake time, but "
                f"{self.wellness_minutes:.0f} minutes of wellness time."
            )

        # Activity and wellness are both subsets of awake time. Their
        # combined duration therefore cannot exceed the available day.
        combined_minutes = self.activity_minutes + self.wellness_minutes
        if combined_minutes > awake_minutes:
            raise ValidationError(
                f"This record is not realistic: you entered {self.sleep_hours:.1f} "
                f"hours of sleep, leaving {awake_minutes:.0f} minutes awake, but "
                f"activity + wellness totals {combined_minutes:.0f} minutes. "
                f"Those activities must fit inside the awake portion of the day."
            )
    @staticmethod
    def validate_date(value) -> str:
        if isinstance(value, datetime.date):
            return value.strftime(DATE_FORMAT)
        if not value or not isinstance(value, str):
            raise ValidationError("Please enter a valid date.")
        try:
            datetime.datetime.strptime(value, DATE_FORMAT)
        except ValueError:
            raise ValidationError("Please enter the date in YYYY-MM-DD format.")
        return value

    @staticmethod
    def _validate_number(field_name: str, value, low: float, high: float) -> float:
        pretty = field_name.replace("_", " ")
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise ValidationError(f"Please enter a valid number for {pretty}.")
        if value < low:
            raise ValidationError(f"{pretty.capitalize()} cannot be negative.")
        if value > high:
            raise ValidationError(
                f"Please enter a {pretty} value between {low} and {high}."
            )
        return value

    @property
    def date_obj(self) -> datetime.date:
        return datetime.datetime.strptime(self.date, DATE_FORMAT).date()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "WellnessRecord":
        return cls(
            date=data["date"],
            sleep_hours=data.get("sleep_hours", 0),
            activity_minutes=data.get("activity_minutes", 0),
            hydration_liters=data.get("hydration_liters", 0),
            wellness_minutes=data.get("wellness_minutes", 0),
            is_demo=bool(data.get("is_demo", False)),
        )
