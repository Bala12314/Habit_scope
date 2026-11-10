"""Plain-CSV local storage. Everything stays on your machine, in `data/`."""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from .models import NUMERIC_FIELDS, Day

DAILY_FILE = "daily_metrics.csv"
APPS_FILE = "app_usage.csv"


def _num(s: str | None):
    if s is None or s.strip() == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def load(data_dir: str | Path) -> list[Day]:
    data_dir = Path(data_dir)
    days: dict[date, Day] = {}
    daily = data_dir / DAILY_FILE
    if daily.exists():
        with daily.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                try:
                    d = date.fromisoformat(row["date"])
                except (KeyError, ValueError):
                    continue
                day = Day(date=d)
                for name in NUMERIC_FIELDS:
                    setattr(day, name, _num(row.get(name)))
                days[d] = day
    apps = data_dir / APPS_FILE
    if apps.exists():
        with apps.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                try:
                    d = date.fromisoformat(row["date"])
                except (KeyError, ValueError):
                    continue
                minutes = _num(row.get("minutes"))
                if minutes is None or not row.get("app"):
                    continue
                days.setdefault(d, Day(date=d)).apps[row["app"]] = minutes
    return [days[d].fill_derived() for d in sorted(days)]


def save(data_dir: str | Path, days: list[Day]) -> None:
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    days = sorted(days, key=lambda d: d.date)
    with (data_dir / DAILY_FILE).open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", *NUMERIC_FIELDS])
        for d in days:
            w.writerow([d.date.isoformat(),
                        *["" if d.get(n) is None else round(d.get(n), 3) for n in NUMERIC_FIELDS]])
    with (data_dir / APPS_FILE).open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "app", "minutes"])
        for d in days:
            for app, m in sorted(d.apps.items()):
                w.writerow([d.date.isoformat(), app, round(m, 1)])


def merge(existing: list[Day], new: list[Day]) -> list[Day]:
    """Merge by date; non-empty new values overwrite old ones."""
    out = {d.date: d for d in existing}
    for n in new:
        cur = out.get(n.date)
        if cur is None:
            out[n.date] = n
            continue
        for name in NUMERIC_FIELDS:
            if n.get(name) is not None:
                setattr(cur, name, n.get(name))
        if n.apps:
            cur.apps.update(n.apps)
        cur.fill_derived()
    return [out[d].fill_derived() for d in sorted(out)]
