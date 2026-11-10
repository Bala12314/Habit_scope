"""Deterministic SYNTHETIC data so you can try LifeLens without connecting a watch.

The fake person has realistic bad habits (late-night scrolling -> short sleep -> low energy
next day) so the analysis has something to find. None of this is real health data.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

from ..models import Day

APP_WEIGHTS = {
    "Instagram": 0.24, "YouTube": 0.2, "WhatsApp": 0.14, "Chrome": 0.1, "Reddit": 0.08,
    "Snapchat": 0.07, "Google Docs": 0.05, "Spotify": 0.04, "Games": 0.08,
}


def generate(days: int = 60, end: date | None = None, seed: int = 7) -> list[Day]:
    rng = random.Random(seed)
    end = end or date.today()
    out: list[Day] = []
    prev_night_screen = 40.0
    for i in range(days):
        d = end - timedelta(days=days - 1 - i)
        weekend = d.weekday() >= 5
        trend = i / max(days - 1, 1)  # slow improvement over time

        # last night's phone use hurts the sleep that ends this morning
        bedtime = rng.gauss(24.7 if weekend else 24.0, 0.6) - 0.25 * trend + prev_night_screen / 150
        sleep = max(3.8, min(9.8, 7.6 - (bedtime - 23.5) * 0.55 - prev_night_screen / 90
                             + rng.gauss(0, 0.4) + 0.5 * trend))
        wake = (bedtime + sleep) % 24
        rested = (sleep - 7) * 0.25  # 0 at 7h

        steps = max(1200, rng.gauss(8200 if weekend else 6400, 1900) * (1 + rested * 0.4) + 1500 * trend)
        workout = max(0, rng.gauss(26, 22) if rng.random() < 0.38 + 0.25 * trend else 0)
        active = max(0, steps / 280 + workout * 0.8 + rng.gauss(0, 8))
        rhr = 62 - rested * 3 + rng.gauss(0, 1.4) - 2 * trend
        hrv = max(15, 48 + rested * 12 + rng.gauss(0, 5) + 4 * trend)

        total_screen = max(90, rng.gauss(400 if weekend else 330, 60) - 80 * trend)
        night = max(0, rng.gauss(55, 30) - 45 * trend + (20 if weekend else 0))
        unlocks = max(30, rng.gauss(115, 20) - 20 * trend)

        apps = {}
        for app, w in APP_WEIGHTS.items():
            apps[app] = round(max(0, total_screen * w * rng.uniform(0.7, 1.3)), 1)

        out.append(Day(
            date=d, steps=round(steps), active_minutes=round(active), workout_minutes=round(workout),
            calories=round(steps * 0.04 + workout * 6 + rng.gauss(150, 25)),
            sleep_hours=round(sleep, 2), bedtime_h=round(bedtime, 2), wake_h=round(wake, 2),
            resting_hr=round(rhr, 1), avg_hr=round(rhr + 17 + rng.gauss(0, 3), 1),
            hrv=round(hrv, 1), spo2=round(min(100, rng.gauss(97, 0.8)), 1),
            screen_min=round(sum(apps.values())), unlocks=round(unlocks),
            night_screen_min=round(night), apps=apps,
        ))
        prev_night_screen = night
    return out
