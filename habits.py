"""Rule-based habit detection: which good/bad habits show up, how often, and where they're heading."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

from ..models import Day, categorize


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    kind: str  # "bad" | "good"
    test: Callable[[Day], bool | None]  # None == not enough data that day
    advice: str


def _lt(field, x):
    return lambda d: None if d.get(field) is None else d.get(field) < x


def _ge(field, x):
    return lambda d: None if d.get(field) is None else d.get(field) >= x


def _social(d: Day):
    return d.category_minutes("social") >= 120 if d.apps else None


def _enough_sleep(d: Day):
    return None if d.sleep_hours is None else 7 <= d.sleep_hours <= 9


def _exercise(d: Day):
    vals = [v for v in (d.workout_minutes, d.active_minutes) if v is not None]
    if not vals:
        return None
    return (d.workout_minutes or 0) >= 20 or (d.active_minutes or 0) >= 30


RULES: list[Rule] = [
    # ---- bad habits ----
    Rule("late_bedtime", "Going to bed after 00:30", "bad", _ge("bedtime_h", 24.5),
         "Pick a fixed 'lights out' time and set a wind-down alarm 45 minutes before it."),
    Rule("short_sleep", "Sleeping under 6.5 hours", "bad", _lt("sleep_hours", 6.5),
         "Protect sleep first: move bedtime 20-30 minutes earlier each week until you reach 7+ hours."),
    Rule("night_scrolling", "Phone use late at night (30+ min)", "bad", _ge("night_screen_min", 30),
         "Charge the phone across the room and use a bedtime downtime/focus mode after 23:00."),
    Rule("heavy_phone", "Screen time over 6 hours", "bad", _ge("screen_min", 360),
         "Set daily app limits on your top 2 apps and move them off your home screen."),
    Rule("compulsive_checking", "120+ phone unlocks", "bad", _ge("unlocks", 120),
         "Turn off non-essential notifications; batch-check messages at set times."),
    Rule("social_binge", "2+ hours on social apps", "bad", _social,
         "Use a per-app timer for social apps and replace one session with a walk or a call."),
    Rule("sedentary", "Fewer than 4,000 steps", "bad", _lt("steps", 4000),
         "Add two 10-minute walks (after lunch and after dinner) - they add ~2,500 steps."),
    # ---- good habits ----
    Rule("steps_goal", "Hitting 8,000+ steps", "good", _ge("steps", 8000),
         "Keep it up - anchor your walks to existing routines."),
    Rule("sleep_enough", "Sleeping 7-9 hours", "good", _enough_sleep,
         "Great base - consistency matters as much as duration."),
    Rule("early_bedtime", "In bed by 23:30", "good", lambda d: None if d.bedtime_h is None else d.bedtime_h <= 23.5,
         "Early nights compound - protect this one."),
    Rule("exercise", "Exercising (20+ min workout or 30+ active min)", "good", _exercise,
         "Schedule workouts like meetings; two fixed days a week is a strong start."),
    Rule("low_screen", "Screen time under 3 hours", "good", _lt("screen_min", 180),
         "Excellent - note what filled the time instead."),
]


@dataclass
class HabitStat:
    rule: Rule
    hits: int
    applicable: int
    rate: float          # 0..1
    trend: float         # recent half rate minus earlier half rate (+ = more frequent)
    current_streak: int  # consecutive most-recent days the rule was true
    longest_streak: int

    @property
    def established(self) -> bool:
        return self.applicable >= 7 and self.rate >= 0.4

    @property
    def improving(self) -> bool:
        """True when the habit is moving in the healthy direction."""
        return self.trend < -0.1 if self.rule.kind == "bad" else self.trend > 0.1

    @property
    def worsening(self) -> bool:
        return self.trend > 0.1 if self.rule.kind == "bad" else self.trend < -0.1


def _rate(flags: list[bool]) -> float:
    return sum(flags) / len(flags) if flags else 0.0


def evaluate(days: list[Day], window: int = 30) -> list[HabitStat]:
    recent = days[-window:]
    stats = []
    for rule in RULES:
        flags = [(d.date, rule.test(d)) for d in recent]
        known = [(dt, f) for dt, f in flags if f is not None]
        if not known:
            continue
        bools = [f for _, f in known]
        half = len(bools) // 2
        trend = _rate(bools[half:]) - _rate(bools[:half]) if half >= 3 else 0.0
        cur = 0
        for f in reversed(bools):
            if not f:
                break
            cur += 1
        longest = run = 0
        for f in bools:
            run = run + 1 if f else 0
            longest = max(longest, run)
        stats.append(HabitStat(rule, sum(bools), len(bools), _rate(bools), trend, cur, longest))
    return stats


def bad_habits(stats: list[HabitStat]) -> list[HabitStat]:
    return sorted((s for s in stats if s.rule.kind == "bad" and s.hits),
                  key=lambda s: s.rate, reverse=True)


def good_habits(stats: list[HabitStat]) -> list[HabitStat]:
    return sorted((s for s in stats if s.rule.kind == "good" and s.hits),
                  key=lambda s: s.rate, reverse=True)


def top_apps(days: list[Day], window: int = 14, n: int = 8) -> list[tuple[str, str, float]]:
    """(app, category, average minutes per day) over the window."""
    recent = [d for d in days[-window:] if d.apps]
    if not recent:
        return []
    totals: dict[str, float] = defaultdict(float)
    for d in recent:
        for app, m in d.apps.items():
            totals[app] += m
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:n]
    return [(a, categorize(a), m / len(recent)) for a, m in ranked]
