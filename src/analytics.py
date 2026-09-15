"""
analytics.py - Wellness analytics engine for HealthBridge.

All scoring/trend/suggestion logic lives here, fully separate from the
UI, so it can be unit-tested independently.

IMPORTANT: This module produces a lifestyle-tracking score only.
It has no medical meaning and must never be presented as a diagnosis.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import List, Dict, Optional

try:
    from .models import User, WellnessRecord
except ImportError:  # pragma: no cover - allows `python tests.py` from src/
    from models import User, WellnessRecord

METRICS = ["sleep_hours", "activity_minutes", "hydration_liters", "wellness_minutes"]

METRIC_LABELS = {
    "sleep_hours": "Sleep",
    "activity_minutes": "Activity",
    "hydration_liters": "Hydration",
    "wellness_minutes": "Wellness",
}

# Configurable scoring weights (must sum to 1.0).
SCORE_WEIGHTS = {
    "achievement": 0.70,
    "consistency": 0.20,
    "trend": 0.10,
}

# Tolerance band for trend classification (percentage change).
TREND_IMPROVING_THRESHOLD = 5.0
TREND_DECLINING_THRESHOLD = -5.0

DISCLAIMER = (
    "This is a lifestyle-tracking score based on your selected goals. "
    "It is not a medical assessment."
)
REPORT_DISCLAIMER = (
    "This report is for personal wellness tracking only and is not medical advice."
)


def _metric_score(value: float, target: float) -> float:
    """Normalize a single metric reading against its target -> 0-100."""
    if target <= 0:
        return 0.0
    return min((value / target) * 100.0, 100.0)


def _pct_change(earlier: float, recent: float) -> float:
    """Safe percentage change, handling zero baselines."""
    if earlier == 0:
        if recent == 0:
            return 0.0
        return 100.0  # any growth from zero counts as fully improving
    return ((recent - earlier) / earlier) * 100.0


def classify_trend(change_pct: float) -> str:
    if change_pct >= TREND_IMPROVING_THRESHOLD:
        return "Improving"
    if change_pct <= TREND_DECLINING_THRESHOLD:
        return "Needs attention"
    return "Stable"


@dataclass
class DayBreakdown:
    date: str
    scores: Dict[str, float]
    overall: float


class WellnessReport:
    """Computes averages, scores, trends and suggestions for a user."""

    def __init__(self, user: User, records: List[WellnessRecord]):
        self.user = user
        self.records = sorted(records, key=lambda r: r.date_obj)

    # -- basic stats ---------------------------------------------------

    def records_in_window(self, days: Optional[int]) -> List[WellnessRecord]:
        if days is None or days >= len(self.records):
            return self.records
        return self.records[-days:]

    def averages(self, days: Optional[int] = None) -> Dict[str, float]:
        recs = self.records_in_window(days)
        if not recs:
            return {m: 0.0 for m in METRICS}
        return {m: statistics.fmean(getattr(r, m) for r in recs) for m in METRICS}

    # -- scoring ---------------------------------------------------------

    def achievement_score(self, days: Optional[int] = None) -> float:
        """Average of per-metric target-achievement scores."""
        recs = self.records_in_window(days)
        if not recs:
            return 0.0
        per_day = []
        for r in recs:
            metric_scores = [
                _metric_score(getattr(r, m), self.user.goals[m]) for m in METRICS
            ]
            per_day.append(statistics.fmean(metric_scores))
        return statistics.fmean(per_day)

    def consistency_score(self, days: Optional[int] = None) -> float:
        """
        How consistently the user logs and maintains habits.
        Combines logging frequency with variability of daily achievement.
        Low variance + frequent logging => high consistency.
        """
        recs = self.records_in_window(days)
        if len(recs) < 2:
            return 100.0 if recs else 0.0

        daily_scores = []
        for r in recs:
            metric_scores = [
                _metric_score(getattr(r, m), self.user.goals[m]) for m in METRICS
            ]
            daily_scores.append(statistics.fmean(metric_scores))

        mean_score = statistics.fmean(daily_scores)
        stdev = statistics.pstdev(daily_scores)
        # Normalize: stdev of 0 -> perfectly consistent (100).
        # stdev >= 50 -> treated as very inconsistent (0).
        variability_penalty = min(stdev / 50.0, 1.0) * 100.0
        consistency = max(0.0, 100.0 - variability_penalty)
        # Slightly reward higher baseline achievement too (a user who is
        # consistently doing well is "consistent" in the everyday sense).
        return round((consistency * 0.7) + (min(mean_score, 100.0) * 0.3), 1)

    def trend_score(self, days: Optional[int] = None) -> float:
        """
        Overall trend expressed as a 0-100 score for blending into the
        final wellness score (50 = stable, higher = improving).
        """
        changes = []
        for m in METRICS:
            change = self.metric_change_pct(m, days)
            if change is not None:
                changes.append(change)
        if not changes:
            return 50.0
        avg_change = statistics.fmean(changes)
        # Map change percentage to a 0-100 scale centered at 50.
        score = 50.0 + avg_change
        return max(0.0, min(100.0, score))

    def metric_change_pct(self, metric: str, days: Optional[int] = None) -> Optional[float]:
        """Compare first half vs second half of the window for one metric."""
        recs = self.records_in_window(days)
        if len(recs) < 2:
            return None
        mid = len(recs) // 2
        earlier = recs[:mid] if mid > 0 else recs[:1]
        recent = recs[mid:] if mid > 0 else recs[1:]
        if not earlier or not recent:
            return None
        earlier_avg = statistics.fmean(getattr(r, metric) for r in earlier)
        recent_avg = statistics.fmean(getattr(r, metric) for r in recent)
        return _pct_change(earlier_avg, recent_avg)

    def metric_trend_label(self, metric: str, days: Optional[int] = None) -> str:
        change = self.metric_change_pct(metric, days)
        if change is None:
            return "Stable"
        return classify_trend(change)

    def wellness_score(self, days: Optional[int] = None) -> float:
        achievement = self.achievement_score(days)
        consistency = self.consistency_score(days)
        trend = self.trend_score(days)
        final = (
            achievement * SCORE_WEIGHTS["achievement"]
            + consistency * SCORE_WEIGHTS["consistency"]
            + trend * SCORE_WEIGHTS["trend"]
        )
        return round(max(0.0, min(100.0, final)), 1)

    # -- improvement / suggestions ---------------------------------------

    def weakest_metric(self, days: Optional[int] = None) -> Optional[str]:
        avgs = self.averages(days)
        if not any(avgs.values()) and not self.records:
            return None
        gaps = {
            m: _metric_score(avgs[m], self.user.goals[m]) for m in METRICS
        }
        return min(gaps, key=gaps.get)

    def strongest_metric(self, days: Optional[int] = None) -> Optional[str]:
        avgs = self.averages(days)
        gaps = {
            m: _metric_score(avgs[m], self.user.goals[m]) for m in METRICS
        }
        return max(gaps, key=gaps.get) if gaps else None

    def best_day(self, days: Optional[int] = None) -> Optional[DayBreakdown]:
        recs = self.records_in_window(days)
        if not recs:
            return None
        best = None
        for r in recs:
            scores = {m: _metric_score(getattr(r, m), self.user.goals[m]) for m in METRICS}
            overall = statistics.fmean(scores.values())
            if best is None or overall > best.overall:
                best = DayBreakdown(date=r.date, scores=scores, overall=overall)
        return best

    def suggestions(self, days: Optional[int] = None) -> List[str]:
        """Friendly, non-medical, non-alarming suggestions."""
        avgs = self.averages(days)
        goals = self.user.goals
        tips = []

        if not self.records:
            return [
                "Log your first day to start seeing personalized suggestions here."
            ]

        if avgs["sleep_hours"] < goals["sleep_hours"]:
            tips.append("Try keeping a consistent bedtime tonight.")
        if avgs["hydration_liters"] < goals["hydration_liters"]:
            tips.append("Consider keeping a water bottle nearby during the day.")
        if avgs["activity_minutes"] < goals["activity_minutes"]:
            tips.append(
                "A short walk or stretching session could help you move closer to your activity goal."
            )
        if avgs["wellness_minutes"] < goals["wellness_minutes"]:
            tips.append(
                "Consider taking a few minutes for reading, music, breathing exercises, hobbies, or quiet time."
            )

        if not tips:
            tips.append(
                "Nice consistency! Keep following the habits that work well for you."
            )

        # Add a light trend-based note.
        declining = [
            m for m in METRICS if self.metric_trend_label(m, days) == "Needs attention"
        ]
        if declining:
            label = METRIC_LABELS[declining[0]]
            tips.append(
                f"Your {label.lower()} has been slightly below your personal target lately — "
                "small steps can help it climb back up."
            )

        return tips[:4]

    def status_text(self, metric: str, days: Optional[int] = None) -> str:
        avgs = self.averages(days) if days else None
        return ""  # reserved for future use; UI computes per-record status directly

    # -- weekly report -----------------------------------------------------

    def weekly_report_text(self) -> str:
        days = 7
        avgs = self.averages(days)
        score = self.wellness_score(days)
        best = self.best_day(days)
        weakest = self.weakest_metric(days)
        strongest = self.strongest_metric(days)
        tips = self.suggestions(days)

        lines = []
        lines.append("HEALTHBRIDGE - WEEKLY WELLNESS REPORT")
        lines.append("=" * 42)
        lines.append(f"User: {self.user.name}")
        lines.append("")
        lines.append("Overview (last 7 logged days)")
        lines.append("-" * 42)
        lines.append(f"Average Sleep:     {avgs['sleep_hours']:.1f} hrs  (target {self.user.goals['sleep_hours']:.1f})")
        lines.append(f"Average Activity:  {avgs['activity_minutes']:.1f} min  (target {self.user.goals['activity_minutes']:.1f})")
        lines.append(f"Average Hydration: {avgs['hydration_liters']:.1f} L    (target {self.user.goals['hydration_liters']:.1f})")
        lines.append(f"Average Wellness:  {avgs['wellness_minutes']:.1f} min  (target {self.user.goals['wellness_minutes']:.1f})")
        lines.append(f"Wellness Score:    {score}/100")
        lines.append("")
        lines.append("Trends")
        lines.append("-" * 42)
        for m in METRICS:
            lines.append(f"{METRIC_LABELS[m]:<10}: {self.metric_trend_label(m, days)}")
        lines.append("")
        if best:
            lines.append(f"Best Day: {best.date} (overall achievement {best.overall:.0f}%)")
        if weakest:
            lines.append(f"Improvement Area: {METRIC_LABELS[weakest]}")
        if strongest:
            lines.append(f"Positive Highlight: {METRIC_LABELS[strongest]} is going well!")
        lines.append("")
        lines.append("Suggestions")
        lines.append("-" * 42)
        for tip in tips:
            lines.append(f"- {tip}")
        lines.append("")
        lines.append(REPORT_DISCLAIMER)
        return "\n".join(lines)
