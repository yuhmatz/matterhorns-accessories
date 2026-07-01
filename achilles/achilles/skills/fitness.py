"""Combat-fitness voice coach.

Voice workout logging, progress against unit standards, weekly summaries,
and a minimum-weight guardrail (never coach *below* the configured floor).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from pathlib import Path

# Example unit standards — adjust to the actual unit's table.
UNIT_STANDARDS = {
    "pushups": 60,        # reps in 2 minutes
    "situps": 70,         # reps in 2 minutes
    "run_3k_seconds": 13 * 60 + 30,
}

MIN_BODYWEIGHT_KG = 62.0  # guardrail: warn when logged weight drops below this


@dataclass
class WorkoutEntry:
    date: str            # ISO date
    kind: str            # "pushups" | "situps" | "run" | "weight" | free text
    value: float
    unit: str            # "reps" | "seconds" | "kg" | ...
    raw: str = ""


class FitnessCoach:
    def __init__(self, log_path: str | Path) -> None:
        self.log_path = Path(log_path)

    def _load(self) -> list[WorkoutEntry]:
        if not self.log_path.is_file():
            return []
        data = json.loads(self.log_path.read_text(encoding="utf-8"))
        return [WorkoutEntry(**e) for e in data]

    def _save(self, entries: list[WorkoutEntry]) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.write_text(
            json.dumps([asdict(e) for e in entries], ensure_ascii=False, indent=1),
            encoding="utf-8",
        )

    def log(self, entry: WorkoutEntry) -> str:
        entries = self._load()
        entries.append(entry)
        self._save(entries)
        note = ""
        if entry.kind == "weight" and entry.value < MIN_BODYWEIGHT_KG:
            note = (f" ⚠ {entry.value:.1f} kg is below your {MIN_BODYWEIGHT_KG:.0f} kg floor — "
                    "prioritize fuel and recovery, not cuts.")
        std = UNIT_STANDARDS.get(entry.kind)
        if std is not None and entry.unit == "reps":
            pct = entry.value / std * 100.0
            note += f" That's {pct:.0f}% of the unit standard ({std})."
        return f"Logged {entry.kind}: {entry.value:g} {entry.unit}.{note}"

    def weekly_summary(self, today: date | None = None) -> str:
        today = today or date.today()
        cutoff = today - timedelta(days=7)
        recent = [e for e in self._load()
                  if datetime.fromisoformat(e.date).date() >= cutoff]
        if not recent:
            return "No workouts logged in the last 7 days. Time to move."
        by_kind: dict[str, list[WorkoutEntry]] = {}
        for e in recent:
            by_kind.setdefault(e.kind, []).append(e)
        parts = [f"{len(recent)} sessions this week."]
        for kind, entries in sorted(by_kind.items()):
            best = max(entries, key=lambda e: e.value if e.unit == "reps" else -e.value)
            parts.append(f"{kind}: {len(entries)}x, best {best.value:g} {best.unit}")
        return " ".join(parts)


def parse_command(command: str, today: date | None = None) -> WorkoutEntry | None:
    """Parse things like 'log 45 pushups', 'weight 63.5', 'ran 3k in 14:10'."""
    today = today or date.today()
    c = command.lower()
    m = re.search(r"(\d+)\s*(push[- ]?ups?|שכיבות)", c)
    if m:
        return WorkoutEntry(today.isoformat(), "pushups", float(m.group(1)), "reps", command)
    m = re.search(r"(\d+)\s*(sit[- ]?ups?|בטן)", c)
    if m:
        return WorkoutEntry(today.isoformat(), "situps", float(m.group(1)), "reps", command)
    m = re.search(r"(weight|משקל)\s*(\d+(?:\.\d+)?)", c)
    if m:
        return WorkoutEntry(today.isoformat(), "weight", float(m.group(2)), "kg", command)
    m = re.search(r"(\d+):(\d\d)", c)
    if m and ("run" in c or "ran" in c or "ריצה" in c or "3k" in c):
        seconds = int(m.group(1)) * 60 + int(m.group(2))
        return WorkoutEntry(today.isoformat(), "run", float(seconds), "seconds", command)
    return None


def make_handler(log_path: str | Path):
    coach = FitnessCoach(log_path)

    def handle(command: str) -> str:
        c = command.lower()
        if "summary" in c or "week" in c or "סיכום" in c:
            return coach.weekly_summary()
        entry = parse_command(command)
        if entry:
            return coach.log(entry)
        return ("Say e.g. '45 pushups', 'weight 63.5', 'ran 3k in 14:10', "
                "or ask for a 'weekly summary'.")
    return handle
