"""
sample_data.py - Generates believable demo data for HealthBridge so the
Dashboard and Trends pages are never empty on first launch.
"""

from __future__ import annotations

import datetime
import random
from typing import List

try:
    from .models import WellnessRecord
except ImportError:  # pragma: no cover - allows `python tests.py` from src/
    from models import WellnessRecord

# Fixed seed for reproducible-but-varied demo data.
_RNG = random.Random(42)


def generate_demo_records(num_days: int = 10) -> List[WellnessRecord]:
    """Generate `num_days` days of varied, believable demo records ending today."""
    records = []
    today = datetime.date.today()

    # Baselines with a gentle upward trend to showcase "Improving" trends.
    base_sleep = 6.6
    base_activity = 20.0
    base_hydration = 1.5
    base_wellness = 8.0

    for i in range(num_days):
        day = today - datetime.timedelta(days=(num_days - 1 - i))
        progress = i / max(num_days - 1, 1)  # 0..1 across the window

        sleep = base_sleep + progress * 1.6 + _RNG.uniform(-0.6, 0.6)
        activity = base_activity + progress * 15 + _RNG.uniform(-8, 8)
        hydration = base_hydration + progress * 0.8 + _RNG.uniform(-0.3, 0.3)
        wellness = base_wellness + progress * 9 + _RNG.uniform(-5, 5)

        record = WellnessRecord(
            date=day.strftime("%Y-%m-%d"),
            sleep_hours=round(max(3.0, sleep), 1),
            activity_minutes=round(max(0.0, activity), 0),
            hydration_liters=round(max(0.2, hydration), 2),
            wellness_minutes=round(max(0.0, wellness), 0),
            is_demo=True,
        )
        records.append(record)

    return records
