"""Core data model: one `Day` record per calendar day."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

NUMERIC_FIELDS = [
    "steps",            # count
    "active_minutes",   # minutes of moderate/vigorous activity
    "workout_minutes",  # minutes of logged workouts
    "calories",         # active kcal burned
    "sleep_hours",      # sleep that ended on this date
    "bedtime_h",        # clock hour you fell asleep; 24.5 == 00:30 (after midnight continues past 24)
    "wake_h",           # clock hour you woke up
    "resting_hr",       # bpm
    "avg_hr",           # bpm
    "hrv",              # ms
    "spo2",             # %
    "screen_min",       # total phone screen time, minutes
    "unlocks",          # phone pickups / unlocks
    "night_screen_min", # phone screen minutes between 23:00 and 05:00 (or after your bedtime target)
]

# Keyword -> category. First match wins. Edit freely.
APP_CATEGORIES = {
    "social": ["instagram", "tiktok", "facebook", "snapchat", "twitter", "x.com", "reddit",
               "threads", "linkedin", "pinterest", "bereal", "sharechat"],
    "video": ["youtube", "netflix", "prime video", "hotstar", "twitch", "disney", "jiocinema"],
    "messaging": ["whatsapp", "telegram", "messenger", "signal", "imessage", "messages", "discord"],
    "games": ["game", "pubg", "bgmi", "roblox", "minecraft", "clash", "candy", "free fire"],
    "productivity": ["docs", "sheets", "slack", "teams", "notion", "outlook", "gmail", "calendar",
                     "drive", "zoom", "meet", "classroom", "word", "excel"],
    "browser": ["chrome", "safari", "firefox", "edge", "brave"],
}


def categorize(app: str) -> str:
    name = app.lower()
    for cat, words in APP_CATEGORIES.items():
        if any(w in name for w in words):
            return cat
    return "other"


@dataclass
class Day:
    date: date
    steps: float | None = None
    active_minutes: float | None = None
    workout_minutes: float | None = None
    calories: float | None = None
    sleep_hours: float | None = None
    bedtime_h: float | None = None
    wake_h: float | None = None
    resting_hr: float | None = None
    avg_hr: float | None = None
    hrv: float | None = None
    spo2: float | None = None
    screen_min: float | None = None
    unlocks: float | None = None
    night_screen_min: float | None = None
    apps: dict[str, float] = field(default_factory=dict)  # app name -> minutes

    def get(self, name: str):
        return getattr(self, name)

    def category_minutes(self, category: str) -> float:
        return sum(m for a, m in self.apps.items() if categorize(a) == category)

    def fill_derived(self) -> "Day":
        if self.screen_min is None and self.apps:
            self.screen_min = sum(self.apps.values())
        return self


def parse_clock(text: str) -> float | None:
    """'23:30' -> 23.5, '00:45' -> 24.75 (bedtimes before noon are treated as after midnight)."""
    text = (text or "").strip()
    if not text:
        return None
    token = next((t for t in text.replace("T", " ").split() if ":" in t), None)
    if token is None:
        return None
    try:
        parts = token.split(":")
        h = int(parts[0]) + int(parts[1]) / 60
    except (ValueError, IndexError):
        return None
    return h + 24 if h < 12 else h


def fmt_clock(h: float) -> str:
    h = h % 24
    hh = int(h)
    mm = int(round((h - hh) * 60))
    if mm == 60:
        hh, mm = (hh + 1) % 24, 0
    return f"{hh:02d}:{mm:02d}"
