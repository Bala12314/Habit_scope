"""Daily performance score (0-100) built from four transparent components.

    activity 30%  - steps and active minutes
    sleep    30%  - duration and bedtime
    recovery 20%  - resting HR / HRV vs YOUR OWN baseline
    digital  20%  - screen time, late-night use, phone pickups

A component is skipped (and the weights renormalised) when its data is missing.
This is a lifestyle heuristic, not a medical measurement.
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from ..models import Day

WEIGHTS = {"activity": 0.30, "sleep": 0.30, "recovery": 0.20, "digital": 0.20}


@dataclass
class Score:
    total: float | None
    components: dict[str, float]

    @property
    def label(self) -> str:
        if self.total is None:
            return "no data"
        return ("great" if self.total >= 80 else "good" if self.total >= 65
                else "okay" if self.total >= 50 else "rough")


def clamp(x: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, x))


def baseline(days: list[Day]) -> dict[str, float]:
    out = {}
    for name in ("resting_hr", "hrv", "steps", "sleep_hours", "bedtime_h", "screen_min"):
        vals = [d.get(name) for d in days if d.get(name) is not None]
        if vals:
            out[name] = median(vals)
    return out


def activity_score(d: Day) -> float | None:
    parts = []
    if d.steps is not None:
        parts.append(clamp(d.steps / 10000 * 100))
    if d.active_minutes is not None:
        parts.append(clamp(d.active_minutes / 30 * 100))
    return sum(parts) / len(parts) if parts else None


def sleep_score(d: Day) -> float | None:
    if d.sleep_hours is None:
        return None
    h = d.sleep_hours
    dur = 100 - (7 - h) * 25 if h < 7 else 100 - (h - 9) * 15 if h > 9 else 100
    dur = clamp(dur)
    if d.bedtime_h is not None and d.bedtime_h > 24:
        dur -= min(30, (d.bedtime_h - 24) * 10)
    return clamp(dur)


def recovery_score(d: Day, base: dict[str, float]) -> float | None:
    parts = []
    if d.resting_hr is not None and "resting_hr" in base:
        parts.append(clamp(100 - max(0, d.resting_hr - base["resting_hr"]) * 10))
    if d.hrv is not None and "hrv" in base and base["hrv"] > 0:
        ratio = d.hrv / base["hrv"]
        parts.append(clamp(50 + (ratio - 0.8) * 125))  # 0.8x->50, 1.2x->100
    return sum(parts) / len(parts) if parts else None


def digital_score(d: Day) -> float | None:
    if d.screen_min is None:
        return None
    s = 100 - clamp((d.screen_min - 180) / (480 - 180) * 100)
    if d.night_screen_min:
        s -= min(40, max(0, d.night_screen_min - 15))
    if d.unlocks:
        s -= min(15, max(0, d.unlocks - 80) * 0.2)
    return clamp(s)


def score_day(d: Day, base: dict[str, float]) -> Score:
    comps = {
        "activity": activity_score(d),
        "sleep": sleep_score(d),
        "recovery": recovery_score(d, base),
        "digital": digital_score(d),
    }
    comps = {k: v for k, v in comps.items() if v is not None}
    if not comps:
        return Score(None, {})
    w = sum(WEIGHTS[k] for k in comps)
    total = sum(v * WEIGHTS[k] for k, v in comps.items()) / w
    return Score(round(total, 1), {k: round(v, 1) for k, v in comps.items()})


def score_all(days: list[Day]) -> list[Score]:
    base = baseline(days)
    return [score_day(d, base) for d in days]
