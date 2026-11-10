"""Import an Apple Health `export.xml` (Health app -> profile picture -> Export All Health Data).

Streams the XML so multi-GB exports work. Apple Watch data -> daily metrics.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from ..models import Day

T = "HKQuantityTypeIdentifier"
SLEEP = "HKCategoryTypeIdentifierSleepAnalysis"


def _dt(s: str) -> datetime:
    return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")


def import_apple_health(path: str | Path, since: date | None = None) -> list[Day]:
    steps: dict[date, float] = defaultdict(float)
    kcal: dict[date, float] = defaultdict(float)
    exercise: dict[date, float] = defaultdict(float)
    hr: dict[date, list[float]] = defaultdict(list)
    rhr: dict[date, list[float]] = defaultdict(list)
    hrv: dict[date, list[float]] = defaultdict(list)
    spo2: dict[date, list[float]] = defaultdict(list)
    sleep_min: dict[date, float] = defaultdict(float)
    sleep_start: dict[date, datetime] = {}
    sleep_end: dict[date, datetime] = {}

    for _, el in ET.iterparse(str(path), events=("end",)):
        if el.tag != "Record":
            el.clear()
            continue
        rtype = el.get("type", "")
        try:
            start, end = _dt(el.get("startDate")), _dt(el.get("endDate"))
        except (TypeError, ValueError):
            el.clear()
            continue
        d = end.date()
        if since and d < since:
            el.clear()
            continue
        raw = el.get("value")
        try:
            val = float(raw) if raw is not None else None
        except ValueError:
            val = None

        if rtype == T + "StepCount" and val is not None:
            steps[d] += val
        elif rtype == T + "ActiveEnergyBurned" and val is not None:
            kcal[d] += val
        elif rtype == T + "AppleExerciseTime" and val is not None:
            exercise[d] += val
        elif rtype == T + "HeartRate" and val is not None:
            hr[d].append(val)
        elif rtype == T + "RestingHeartRate" and val is not None:
            rhr[d].append(val)
        elif rtype == T + "HeartRateVariabilitySDNN" and val is not None:
            hrv[d].append(val)
        elif rtype == T + "OxygenSaturation" and val is not None:
            spo2[d].append(val * 100 if val <= 1 else val)
        elif rtype == SLEEP and "Asleep" in (raw or ""):
            sleep_min[d] += (end - start).total_seconds() / 60
            if d not in sleep_start or start < sleep_start[d]:
                sleep_start[d] = start
            if d not in sleep_end or end > sleep_end[d]:
                sleep_end[d] = end
        el.clear()

    all_dates = set(steps) | set(kcal) | set(exercise) | set(hr) | set(rhr) | set(hrv) \
        | set(spo2) | set(sleep_min)
    avg = lambda xs: sum(xs) / len(xs) if xs else None  # noqa: E731
    days = []
    for d in sorted(all_dates):
        day = Day(date=d)
        day.steps = steps.get(d)
        day.calories = kcal.get(d)
        day.active_minutes = exercise.get(d)
        day.avg_hr, day.resting_hr = avg(hr[d]), avg(rhr[d])
        day.hrv, day.spo2 = avg(hrv[d]), avg(spo2[d])
        if d in sleep_min:
            day.sleep_hours = sleep_min[d] / 60
            s, e = sleep_start[d], sleep_end[d]
            sh = s.hour + s.minute / 60
            day.bedtime_h = sh + 24 if sh < 12 else sh
            day.wake_h = e.hour + e.minute / 60
        days.append(day)
    return days
