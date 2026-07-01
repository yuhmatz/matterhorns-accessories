import tempfile
import unittest
from datetime import date
from pathlib import Path

from achilles.skills import fitness


class TestParse(unittest.TestCase):
    def test_pushups(self):
        e = fitness.parse_command("log 45 pushups", today=date(2026, 7, 1))
        self.assertEqual((e.kind, e.value, e.unit), ("pushups", 45.0, "reps"))

    def test_weight(self):
        e = fitness.parse_command("weight 63.5", today=date(2026, 7, 1))
        self.assertEqual((e.kind, e.value, e.unit), ("weight", 63.5, "kg"))

    def test_run(self):
        e = fitness.parse_command("ran 3k in 14:10", today=date(2026, 7, 1))
        self.assertEqual((e.kind, e.value), ("run", 14 * 60 + 10))

    def test_hebrew_pushups(self):
        e = fitness.parse_command("40 שכיבות", today=date(2026, 7, 1))
        self.assertEqual((e.kind, e.value), ("pushups", 40.0))

    def test_unparseable(self):
        self.assertIsNone(fitness.parse_command("hello there"))


class TestCoach(unittest.TestCase):
    def test_log_standard_and_guardrail(self):
        with tempfile.TemporaryDirectory() as tmp:
            coach = fitness.FitnessCoach(Path(tmp) / "w.json")
            msg = coach.log(fitness.WorkoutEntry("2026-07-01", "pushups", 45, "reps"))
            self.assertIn("75%", msg)  # 45/60 of the unit standard

            warn = coach.log(fitness.WorkoutEntry("2026-07-01", "weight", 60.0, "kg"))
            self.assertIn("below", warn)

            ok = coach.log(fitness.WorkoutEntry("2026-07-01", "weight", 66.0, "kg"))
            self.assertNotIn("below", ok)

    def test_weekly_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            coach = fitness.FitnessCoach(Path(tmp) / "w.json")
            self.assertIn("No workouts", coach.weekly_summary(today=date(2026, 7, 1)))
            coach.log(fitness.WorkoutEntry("2026-06-28", "pushups", 40, "reps"))
            coach.log(fitness.WorkoutEntry("2026-06-30", "pushups", 50, "reps"))
            coach.log(fitness.WorkoutEntry("2026-06-01", "pushups", 99, "reps"))  # too old
            summary = coach.weekly_summary(today=date(2026, 7, 1))
            self.assertIn("2 sessions", summary)
            self.assertIn("best 50", summary)


if __name__ == "__main__":
    unittest.main()
