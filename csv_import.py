"""Import generic CSV exports (Fitbit / Garmin / Google Fit / Samsung Health / manual logs).

Column names are matched case-insensitively against a list of aliases, so most exports
work without renaming. Use `--map our_col=their_col` on the CLI for anything unusual.
"""
from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path

from ..models import Day, parse_clock

ALIASES: dict[str, list[str]] = {
    "steps": ["steps", "step_count", "stepcount", "total_steps"],
    "active_minutes": ["active_minutes", "active_min", "exercise_minutes", "activeminutes",
                       "active_zone_minutes", "move_minutes"],
    "workout_minutes": ["workout_minutes", "workout_min", "workout_duration_min"],
    "calories": ["calories", "calories_burned", "active_calories", "kcal", "calories_active"],
    "sleep_hours": ["sleep_hours", "sleep_h", "sleep_duration_h", "hours_asleep"],
    "sleep_minutes": ["sleep_minutes", "minutes_asleep", "sleep_duration_min", "sleep_duration"],
    "bedtime": ["bedtime", "sleep_start", "bed_time", "start_time_sleep"],
    "wake": ["wake", "wake_time", "sleep_end", "wakeup"],
    "resting_hr": ["resting_hr", "resting_heart_rate", "rhr", "resting_heartrate"],
    "avg_hr": ["avg_hr", "average_heart_rate", "avg_heart_rate", "heart_rate_avg"],
    "hrv": ["hrv", "heart_rate_variability", "hrv_ms"],
    "spo2": ["spo2", "oxygen_saturation", "blood_oxygen"],
    "screen_min": ["screen_min", "screen_time_min", "screen_minutes", "screen_time", "phone_minutes"],
    "unlocks": ["unlocks", "pickups", "phone_pickups", "phone_unlocks"],
    "night_screen_min": ["night_screen_min", "night_screen_minutes", "late_night_screen_min"],
}
DATE_ALIASES = ["date", "day", "timestamp", "datetime"]


def _norm(h: str) -> str:
    return h.strip().lower().replace(" ", "_").replace("-", "_")


def parse_date(text: str) -> date | None:
    text = (text or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        pass
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%d %b %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text.split(" ")[0] if fmt.count(" ") == 0 else text, fmt).date()
        except ValueError:
            continue
    return None


def _to_float(s: str | None):
    if s is None:
        return None
    s = s.strip().replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def import_daily_csv(path: str | Path, mapping: dict[str, str] | None = None) -> tuple[list[Day], int]:
    """Return (days, skipped_rows). `mapping` maps our field -> their column name."""
    mapping = {k: _norm(v) for k, v in (mapping or {}).items()}
    days: list[Day] = []
    skipped = 0
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = {_norm(h): h for h in (reader.fieldnames or [])}

        def col(field: str) -> str | None:
            if field in mapping and mapping[field] in headers:
                return headers[mapping[field]]
            for alias in ALIASES.get(field, []):
                if alias in headers:
                    return headers[alias]
            return None

        date_col = next((headers[a] for a in DATE_ALIASES if a in headers), None)
        if mapping.get("date") in headers:
            date_col = headers[mapping["date"]]
        if date_col is None:
            raise ValueError(f"No date column found. Headers: {list(headers.values())}")
        cols = {field: col(field) for field in ALIASES}

        for row in reader:
            d = parse_date(row.get(date_col, ""))
            if d is None:
                skipped += 1
                continue
            day = Day(date=d)
            for field in ("steps", "active_minutes", "workout_minutes", "calories", "resting_hr",
                          "avg_hr", "hrv", "spo2", "screen_min", "unlocks", "night_screen_min",
                          "sleep_hours"):
                if cols[field]:
                    setattr(day, field, _to_float(row.get(cols[field])))
            if day.sleep_hours is None and cols["sleep_minutes"]:
                m = _to_float(row.get(cols["sleep_minutes"]))
                day.sleep_hours = None if m is None else m / 60
            if cols["bedtime"]:
                day.bedtime_h = parse_clock(row.get(cols["bedtime"], ""))
            if cols["wake"]:
                w = parse_clock(row.get(cols["wake"], ""))
                day.wake_h = None if w is None else w % 24
            days.append(day)
    return days, skipped


def import_app_usage_csv(path: str | Path) -> tuple[list[Day], int]:
    """CSV with columns: date, app, minutes  (optional: night_minutes).

    Android Digital Wellbeing / iOS Screen Time have no official export, so this is the
    neutral format. See docs/DATA_SOURCES.md for ways to produce it.
    """
    by_date: dict[date, Day] = {}
    skipped = 0
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = {_norm(h): h for h in (reader.fieldnames or [])}
        for needed in ("date", "app", "minutes"):
            if needed not in headers:
                raise ValueError(f"app usage CSV needs columns date, app, minutes (missing {needed})")
        night = headers.get("night_minutes")
        for row in reader:
            d = parse_date(row[headers["date"]])
            m = _to_float(row[headers["minutes"]])
            app = (row[headers["app"]] or "").strip()
            if d is None or m is None or not app:
                skipped += 1
                continue
            day = by_date.setdefault(d, Day(date=d))
            day.apps[app] = day.apps.get(app, 0) + m
            if night:
                nm = _to_float(row.get(night))
                if nm:
                    day.night_screen_min = (day.night_screen_min or 0) + nm
    return [d.fill_derived() for d in by_date.values()], skipped
