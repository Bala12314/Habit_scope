"""The 'assistant' layer: turns analysis into a daily brief, and optionally asks an LLM.

The brief is fully rule-based and works offline. `ask()` is optional: if ANTHROPIC_API_KEY is
set it sends a compact *summary* (never raw rows) to the API so you can ask free-form questions.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .analysis import habits as H
from .analysis import insights as I
from .analysis import score as S
from .models import Day, fmt_clock

DISCLAIMER = "LifeLens gives lifestyle suggestions, not medical advice. Talk to a doctor about health concerns."


def _round_to(x: float, step: int) -> int:
    return int(round(x / step) * step)


def targets(days: list[Day]) -> dict[str, str]:
    """Personalised, gently-progressive targets for today."""
    base = S.baseline(days)
    t: dict[str, str] = {}
    if "steps" in base:
        goal = min(10000, max(6000, base["steps"] * 1.1))
        t["steps"] = f"{_round_to(goal, 500):,} steps (your median is {base['steps']:,.0f})"
    if "bedtime_h" in base:
        goal = max(23.0, min(base["bedtime_h"] - 0.5, 23.5)) if base["bedtime_h"] > 23.5 else base["bedtime_h"]
        t["bedtime"] = f"lights out by {fmt_clock(goal)} (your median is {fmt_clock(base['bedtime_h'])})"
        t["phone cutoff"] = f"phone down by {fmt_clock(goal - 1)}"
    if "screen_min" in base:
        goal = min(360, base["screen_min"] * 0.9)
        t["screen time"] = f"under {goal / 60:.1f} h (your median is {base['screen_min'] / 60:.1f} h)"
    if "sleep_hours" in base and base["sleep_hours"] < 7:
        t["sleep"] = "aim for 7+ hours tonight"
    return t


def daily_brief(days: list[Day]) -> str:
    if not days:
        return "No data yet. Run `lifelens demo` or import your data first."
    base = S.baseline(days)
    scores = [S.score_day(d, base) for d in days]
    last, sc = days[-1], scores[-1]
    stats = H.evaluate(days, 30)
    bad = [s for s in H.bad_habits(stats) if s.established]
    good = H.good_habits(stats)
    lines = []

    if sc.total is None:
        lines.append(f"{last.date}: not enough data to score this day.")
    else:
        week = [s.total for s in scores[-7:] if s.total is not None]
        avg7 = sum(week) / len(week) if week else sc.total
        arrow = "above" if sc.total > avg7 + 3 else "below" if sc.total < avg7 - 3 else "in line with"
        lines.append(f"{last.date}: score {sc.total:.0f}/100 ({sc.label}), {arrow} your 7-day average of {avg7:.0f}.")
        if sc.components:
            best = max(sc.components, key=sc.components.get)
            worst = min(sc.components, key=sc.components.get)
            lines.append(f"  Strongest: {best} ({sc.components[best]:.0f}).  Weakest: {worst} ({sc.components[worst]:.0f}).")

    if bad:
        focus = bad[0]
        lines += ["", f"This week's ONE focus: {focus.rule.name}",
                  f"  It happened on {focus.hits} of the last {focus.applicable} days"
                  + (" and is getting worse." if focus.worsening else " and is improving." if focus.improving else "."),
                  f"  Try this: {focus.rule.advice}"]
        others = [s.rule.name for s in bad[1:3]]
        if others:
            lines.append(f"  Also watch: {'; '.join(others)}.")
    else:
        lines += ["", "No established bad habits in the last 30 days. Nice work."]

    if good:
        g = good[0]
        extra = f" (current streak: {g.current_streak} days)" if g.current_streak >= 2 else ""
        lines += ["", f"Keep going: {g.rule.name} - {g.hits}/{g.applicable} days{extra}."]

    t = targets(days)
    if t:
        lines += ["", "Today's targets:"] + [f"  - {k}: {v}" for k, v in t.items()]

    ins = I.find_insights(days)
    if ins:
        lines += ["", "What your data says about you:", f"  - {ins[0].text}"]

    lines += ["", DISCLAIMER]
    return "\n".join(lines)


def build_context(days: list[Day], window: int = 30) -> dict:
    """Compact, aggregated summary suitable for sending to an LLM (no raw per-day rows)."""
    recent = days[-window:]
    base = S.baseline(recent)
    scores = [S.score_day(d, base).total for d in recent]
    scores = [s for s in scores if s is not None]
    stats = H.evaluate(days, window)
    return {
        "window_days": len(recent),
        "medians": {k: round(v, 2) for k, v in base.items()},
        "average_score": round(sum(scores) / len(scores), 1) if scores else None,
        "bad_habits": [{"name": s.rule.name, "days": f"{s.hits}/{s.applicable}", "trend": round(s.trend, 2)}
                       for s in H.bad_habits(stats)],
        "good_habits": [{"name": s.rule.name, "days": f"{s.hits}/{s.applicable}"} for s in H.good_habits(stats)],
        "top_apps_min_per_day": [{"app": a, "category": c, "minutes": round(m)} for a, c, m in H.top_apps(days)],
        "insights": [i.text for i in I.find_insights(days)],
    }


def ask(days: list[Day], question: str, model: str | None = None) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return ("Set ANTHROPIC_API_KEY to enable free-form questions. "
                "Meanwhile, here's your rule-based brief:\n\n" + daily_brief(days))
    system = ("You are a supportive personal wellbeing coach. Use ONLY the JSON summary of the user's "
              "smartwatch/phone data. Be specific, kind and concise; suggest 1-3 small actions; "
              "do not diagnose or give medical advice.")
    body = {
        "model": model or os.environ.get("LIFELENS_MODEL", "claude-sonnet-5-5"),
        "max_tokens": 700,
        "system": system,
        "messages": [{"role": "user",
                      "content": f"My data summary:\n{json.dumps(build_context(days), indent=2)}\n\nQuestion: {question}"}],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)
        return "".join(b.get("text", "") for b in data.get("content", [])) + f"\n\n{DISCLAIMER}"
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        return f"Could not reach the API ({e}). Rule-based brief instead:\n\n" + daily_brief(days)
