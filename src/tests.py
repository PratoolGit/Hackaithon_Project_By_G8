"""
tests.py - Unit tests for HealthBridge core logic.

Run with:
    python tests.py
or:
    python -m unittest tests.py -v

Note: these tests cover models, analytics, storage, and the app
controller (all pure Python / no GUI). They do not launch the Qt GUI, since automated GUI testing is out of scope for a hackathon prototype.
"""

import json
import tempfile
import unittest
from pathlib import Path

try:
    from .models import User, WellnessRecord, ValidationError
    from .analytics import WellnessReport, classify_trend
    from .storage import Storage
    from .app import HealthBridgeApp
except ImportError:  # pragma: no cover - allows `python tests.py` from src/
    from models import User, WellnessRecord, ValidationError
    from analytics import WellnessReport, classify_trend
    from storage import Storage
    from app import HealthBridgeApp


class TestUserValidation(unittest.TestCase):
    def test_valid_user(self):
        u = User(name="Asha", age=21)
        self.assertEqual(u.name, "Asha")
        self.assertEqual(u.age, 21)

    def test_empty_name_rejected(self):
        with self.assertRaises(ValidationError):
            User(name="   ")

    def test_invalid_age_rejected(self):
        with self.assertRaises(ValidationError):
            User(name="Asha", age=200)

    def test_default_goals_applied(self):
        u = User(name="Asha")
        self.assertEqual(u.goals["sleep_hours"], 8.0)

    def test_set_goal_rejects_negative(self):
        u = User(name="Asha")
        with self.assertRaises(ValidationError):
            u.set_goal("sleep_hours", -1)

    def test_set_goal_rejects_zero(self):
        u = User(name="Asha")
        with self.assertRaises(ValidationError):
            u.set_goal("hydration_liters", 0)


class TestWellnessRecordValidation(unittest.TestCase):
    def test_valid_record(self):
        r = WellnessRecord("2026-09-01", 7.5, 30, 2.0, 15)
        self.assertEqual(r.sleep_hours, 7.5)

    def test_negative_sleep_rejected(self):
        with self.assertRaises(ValidationError):
            WellnessRecord("2026-09-01", -1, 30, 2.0, 15)

    def test_negative_activity_rejected(self):
        with self.assertRaises(ValidationError):
            WellnessRecord("2026-09-01", 7, -5, 2.0, 15)

    def test_negative_hydration_rejected(self):
        with self.assertRaises(ValidationError):
            WellnessRecord("2026-09-01", 7, 30, -1, 15)

    def test_negative_wellness_rejected(self):
        with self.assertRaises(ValidationError):
            WellnessRecord("2026-09-01", 7, 30, 2.0, -5)

    def test_invalid_date_rejected(self):
        with self.assertRaises(ValidationError):
            WellnessRecord("01-09-2026", 7, 30, 2.0, 15)

    def test_out_of_range_rejected(self):
        with self.assertRaises(ValidationError):
            WellnessRecord("2026-09-01", 30, 30, 2.0, 15)  # 30 hrs sleep impossible

    def test_activity_and_wellness_must_fit_inside_awake_time(self):
        with self.assertRaises(ValidationError):
            # 20h sleep leaves only 240 awake minutes; 180 + 80 = 260.
            WellnessRecord("2026-09-01", 20, 180, 2.0, 80)


class TestAnalytics(unittest.TestCase):
    def setUp(self):
        self.user = User(name="Test", goals={
            "sleep_hours": 8, "activity_minutes": 30, "hydration_liters": 2, "wellness_minutes": 15
        })

    def _records(self, days_values):
        recs = []
        for date, sleep, act, hyd, well in days_values:
            recs.append(WellnessRecord(date, sleep, act, hyd, well))
        return recs

    def test_averages(self):
        recs = self._records([
            ("2026-09-01", 8, 30, 2, 15),
            ("2026-09-02", 6, 30, 2, 15),
        ])
        report = WellnessReport(self.user, recs)
        self.assertAlmostEqual(report.averages()["sleep_hours"], 7.0)

    def test_achievement_score_full_target(self):
        recs = self._records([("2026-09-01", 8, 30, 2, 15)])
        report = WellnessReport(self.user, recs)
        self.assertAlmostEqual(report.achievement_score(), 100.0)

    def test_achievement_score_half_target(self):
        recs = self._records([("2026-09-01", 4, 15, 1, 7.5)])
        report = WellnessReport(self.user, recs)
        self.assertAlmostEqual(report.achievement_score(), 50.0, delta=0.5)

    def test_wellness_score_bounds(self):
        recs = self._records([("2026-09-01", 8, 30, 2, 15)])
        report = WellnessReport(self.user, recs)
        score = report.wellness_score()
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_trend_improving(self):
        recs = self._records([
            ("2026-09-01", 5, 10, 1, 5),
            ("2026-09-02", 5, 10, 1, 5),
            ("2026-09-03", 8, 30, 2, 15),
            ("2026-09-04", 8, 30, 2, 15),
        ])
        report = WellnessReport(self.user, recs)
        self.assertEqual(report.metric_trend_label("sleep_hours"), "Improving")

    def test_trend_declining(self):
        recs = self._records([
            ("2026-09-01", 8, 30, 2, 15),
            ("2026-09-02", 8, 30, 2, 15),
            ("2026-09-03", 4, 10, 1, 5),
            ("2026-09-04", 4, 10, 1, 5),
        ])
        report = WellnessReport(self.user, recs)
        self.assertEqual(report.metric_trend_label("sleep_hours"), "Needs attention")

    def test_trend_stable(self):
        recs = self._records([
            ("2026-09-01", 7.5, 30, 2, 15),
            ("2026-09-02", 7.6, 30, 2, 15),
            ("2026-09-03", 7.4, 30, 2, 15),
            ("2026-09-04", 7.5, 30, 2, 15),
        ])
        report = WellnessReport(self.user, recs)
        self.assertEqual(report.metric_trend_label("sleep_hours"), "Stable")

    def test_trend_zero_baseline_handled_safely(self):
        recs = self._records([
            ("2026-09-01", 0, 0, 0, 0),
            ("2026-09-02", 0, 0, 0, 0),
            ("2026-09-03", 5, 20, 1, 10),
            ("2026-09-04", 5, 20, 1, 10),
        ])
        report = WellnessReport(self.user, recs)
        # Should not raise ZeroDivisionError.
        label = report.metric_trend_label("activity_minutes")
        self.assertIn(label, ("Improving", "Stable", "Needs attention"))

    def test_classify_trend_boundaries(self):
        self.assertEqual(classify_trend(5.0), "Improving")
        self.assertEqual(classify_trend(-5.0), "Needs attention")
        self.assertEqual(classify_trend(0.0), "Stable")

    def test_weakest_metric(self):
        recs = self._records([("2026-09-01", 8, 30, 0.2, 15)])
        report = WellnessReport(self.user, recs)
        self.assertEqual(report.weakest_metric(), "hydration_liters")

    def test_suggestions_not_empty(self):
        recs = self._records([("2026-09-01", 4, 5, 0.5, 2)])
        report = WellnessReport(self.user, recs)
        tips = report.suggestions()
        self.assertTrue(len(tips) > 0)
        for tip in tips:
            self.assertNotIn("disorder", tip.lower())
            self.assertNotIn("unhealthy", tip.lower())

    def test_no_records_suggestions(self):
        report = WellnessReport(self.user, [])
        tips = report.suggestions()
        self.assertEqual(len(tips), 1)


class TestDuplicateDetection(unittest.TestCase):
    def test_find_record_detects_duplicate_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = Storage(Path(tmp) / "data.json")
            app = HealthBridgeApp(storage)
            app.complete_onboarding("Test", 20, {})
            app.add_or_update_record("2026-09-01", 7, 30, 2, 15)
            self.assertIsNotNone(app.find_record("2026-09-01"))
            self.assertIsNone(app.find_record("2026-09-02"))

    def test_update_existing_record_replaces_not_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = Storage(Path(tmp) / "data.json")
            app = HealthBridgeApp(storage)
            app.complete_onboarding("Test", 20, {})
            app.add_or_update_record("2026-09-01", 7, 30, 2, 15)
            app.add_or_update_record("2026-09-01", 9, 40, 3, 20)
            same_date_records = [r for r in app.records if r.date == "2026-09-01"]
            self.assertEqual(len(same_date_records), 1)
            self.assertEqual(same_date_records[0].sleep_hours, 9)


class TestStorage(unittest.TestCase):
    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            storage = Storage(path)
            user = User(name="Roundtrip", age=30)
            records = [WellnessRecord("2026-09-01", 7, 30, 2, 15)]
            storage.save(user, records, True, False, "dark")

            loaded_user, loaded_records, onboarded, demo, theme = storage.load()
            self.assertEqual(loaded_user.name, "Roundtrip")
            self.assertEqual(len(loaded_records), 1)
            self.assertTrue(onboarded)
            self.assertFalse(demo)
            self.assertEqual(theme, "dark")

    def test_theme_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            storage = Storage(path)
            user = User(name="Theme Tester")
            storage.save(user, [], True, False, "light")

            _, _, _, _, theme = storage.load()
            self.assertEqual(theme, "light")

    def test_invalid_theme_falls_back_to_dark(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            path.write_text(
                json.dumps({"user": {}, "records": [], "onboarded": False,
                            "demo_loaded": False, "theme": "not-a-real-theme"}),
                encoding="utf-8",
            )
            storage = Storage(path)
            _, _, _, _, theme = storage.load()
            self.assertEqual(theme, "dark")

    def test_missing_file_returns_empty_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "does_not_exist.json"
            storage = Storage(path)
            user, records, onboarded, demo, theme = storage.load()
            self.assertEqual(records, [])
            self.assertFalse(onboarded)

    def test_corrupted_json_recovers_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            path.write_text("{ this is not valid json ][", encoding="utf-8")
            storage = Storage(path)
            user, records, onboarded, demo, theme = storage.load()
            self.assertEqual(records, [])
            # A backup of the corrupted file should have been made.
            self.assertTrue((path.with_suffix(".corrupted.bak")).exists())

    def test_malformed_individual_record_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            data = {
                "user": {"name": "Test"},
                "records": [
                    {"date": "2026-09-01", "sleep_hours": 7, "activity_minutes": 30,
                     "hydration_liters": 2, "wellness_minutes": 15},
                    {"date": "bad-date", "sleep_hours": -5, "activity_minutes": 30,
                     "hydration_liters": 2, "wellness_minutes": 15},
                ],
                "onboarded": True,
                "demo_loaded": False,
            }
            path.write_text(json.dumps(data), encoding="utf-8")
            storage = Storage(path)
            user, records, onboarded, demo, theme = storage.load()
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].date, "2026-09-01")

    def test_empty_data_handling(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            path.write_text("", encoding="utf-8")
            storage = Storage(path)
            user, records, onboarded, demo, theme = storage.load()
            self.assertEqual(records, [])


class TestAppController(unittest.TestCase):
    def test_demo_data_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = Storage(Path(tmp) / "data.json")
            app = HealthBridgeApp(storage)
            app.complete_onboarding("Test", 20, {})
            app.load_demo_data()
            self.assertTrue(any(r.is_demo for r in app.records))
            app.clear_demo_data()
            self.assertFalse(any(r.is_demo for r in app.records))

    def test_reset_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = Storage(Path(tmp) / "data.json")
            app = HealthBridgeApp(storage)
            app.complete_onboarding("Test", 20, {})
            app.add_or_update_record("2026-09-01", 7, 30, 2, 15)
            app.reset_all()
            self.assertEqual(app.records, [])
            self.assertFalse(app.onboarded)

    def test_delete_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = Storage(Path(tmp) / "data.json")
            app = HealthBridgeApp(storage)
            app.complete_onboarding("Test", 20, {})
            app.add_or_update_record("2026-09-01", 7, 30, 2, 15)
            self.assertTrue(app.delete_record("2026-09-01"))
            self.assertFalse(app.delete_record("2026-09-01"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
