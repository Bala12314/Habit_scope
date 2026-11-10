"""Find relationships in YOUR data (e.g. 'late-night phone use -> less sleep').

Correlation is not causation: insights are phrased as tendencies, and only shown when there
are enough days and the relationship is not trivially weak.
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import StatisticsError, correlation, mean, median

from ..models import Day

MIN_DAYS = 14
MIN_ABS_R = 0.3

# (cause field, effect field, lag in days, label cause, label effect, unit)
PAIRS = [
    ("night_screen_min", "sleep_hours", 1, "late-night phone use", "the next night's sleep", "h"),
    ("bedtime_h", "sleep_hours", 0, "a later bedtime", "sleep duration", "h"),
    ("sleep_hours", "steps", 0, "more sleep", "steps that day", " steps"),
    ("sleep_hours", "resting_hr", 0, "more sleep", "resting heart rate", " bpm"),
    ("steps", "sleep_hours", 1, "more steps", "the next night's sleep", "h"),
    ("screen_min", "steps", 0, "more screen time", "steps that day", " steps"),
    ("workout_minutes", "hrv", 1, "working out", "next-day HRV", " ms"),
]


@dataclass
class Insight:
    cause: str
    effect: str
    r: float
    n: int
    high_avg: float
    low_avg: float
    unit: str
    text: str


def paired(days: list[Day], cause: str, effect: str, lag: int) -> list[tuple[float, float]]:
    out = []
    for i in range(len(days) - lag):
        x, y = days[i].get(cause), days[i + lag].get(effect)
        if x is not None and y is not None and (lag == 0 or (days[i + lag].date - days[i].date).days == lag):
            out.append((x, y))
    return out


def find_insights(days: list[Day]) -> list[Insight]:
    results = []
    for cause, effect, lag, c_lab, e_lab, unit in PAIRS:
        pts = paired(days, cause, effect, lag)
        if len(pts) < MIN_DAYS:
            continue
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        try:
            r = correlation(xs, ys)
        except StatisticsError:  # constant input
            continue
        if abs(r) < MIN_ABS_R:
            continue
        cut = median(xs)
        hi = [y for x, y in pts if x > cut]
        lo = [y for x, y in pts if x <= cut]
        if not hi or not lo:
            continue
        hi_avg, lo_avg = mean(hi), mean(lo)
        fmt = (lambda v: f"{v:,.0f}") if unit.strip() == "steps" else (lambda v: f"{v:.1f}")
        text = (f"When you have {c_lab} (above your median), {e_lab} averages "
                f"{fmt(hi_avg)}{unit} vs {fmt(lo_avg)}{unit} otherwise "
                f"(r={r:+.2f}, {len(pts)} days).")
        results.append(Insight(c_lab, e_lab, r, len(pts), hi_avg, lo_avg, unit, text))
    return sorted(results, key=lambda i: abs(i.r), reverse=True)


def weekly_change(days: list[Day]) -> list[tuple[str, float, float]]:
    """(metric, last-7-day mean, previous-7-day mean) for key metrics."""
    last, prev = days[-7:], days[-14:-7]
    out = []
    for name in ("steps", "sleep_hours", "screen_min", "night_screen_min", "resting_hr", "hrv"):
        a = [d.get(name) for d in last if d.get(name) is not None]
        b = [d.get(name) for d in prev if d.get(name) is not None]
        if len(a) >= 3 and len(b) >= 3:
            out.append((name, mean(a), mean(b)))
    return out
