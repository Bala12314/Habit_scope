"""Command line interface:  python -m lifelens <command>"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

from . import __version__, assistant, report, storage
from .analysis import habits as H
from .analysis import insights as I
from .analysis import score as S
from .ingest import apple_health, csv_import, sample


def _load(args) -> list:
    days = storage.load(args.data_dir)
    if not days:
        sys.exit(f"No data found in '{args.data_dir}'. Try:  python -m lifelens demo")
    return days


def cmd_demo(args):
    days = sample.generate(args.days)
    storage.save(args.data_dir, days)
    print(f"Wrote {len(days)} days of SYNTHETIC sample data to {args.data_dir}/")
    print("Next: python -m lifelens today   |   python -m lifelens report")


def cmd_import(args):
    existing = storage.load(args.data_dir)
    if args.kind == "apple-health":
        new = apple_health.import_apple_health(args.path, since=date.fromisoformat(args.since) if args.since else None)
        skipped = 0
    elif args.kind == "apps":
        new, skipped = csv_import.import_app_usage_csv(args.path)
    else:
        mapping = dict(m.split("=", 1) for m in (args.map or []))
        new, skipped = csv_import.import_daily_csv(args.path, mapping)
    merged = storage.merge(existing, new)
    storage.save(args.data_dir, merged)
    print(f"Imported {len(new)} days ({skipped} rows skipped). Total days stored: {len(merged)}.")


def cmd_today(args):
    print(assistant.daily_brief(_load(args)))


def cmd_habits(args):
    days = _load(args)
    stats = H.evaluate(days, args.window)
    print(f"Habits over the last {min(args.window, len(days))} days\n")
    for title, items in (("Bad habits", H.bad_habits(stats)), ("Good habits", H.good_habits(stats))):
        print(title)
        for s in items:
            trend = "improving" if s.improving else "worsening" if s.worsening else "steady"
            print(f"  {s.hits:>2}/{s.applicable:<2} days  {s.rule.name}  [{trend}]")
        if not items:
            print("  (none detected)")
        print()
    print("Top apps (avg min/day, last 14 days)")
    for app, cat, m in H.top_apps(days):
        print(f"  {m:5.0f}  {app} ({cat})")


def cmd_insights(args):
    days = _load(args)
    ins = I.find_insights(days)
    print("\n".join(f"- {i.text}" for i in ins) or "Not enough data for patterns yet (need ~2 weeks).")


def cmd_score(args):
    days = _load(args)
    base = S.baseline(days)
    print("date        score  activity sleep recovery digital")
    for d in days[-args.window:]:
        sc = S.score_day(d, base)
        c = sc.components
        cell = lambda k: f"{c[k]:7.0f}" if k in c else "      -"  # noqa: E731
        print(f"{d.date}  {'-' if sc.total is None else f'{sc.total:5.0f}':>5} {cell('activity')} "
              f"{cell('sleep')} {cell('recovery')} {cell('digital')}")


def cmd_report(args):
    days = _load(args)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report.render(days, args.window), encoding="utf-8")
    print(f"Report written to {out}")


def cmd_ask(args):
    print(assistant.ask(_load(args), " ".join(args.question)))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lifelens", description="LifeLens - analyze your daily life from watch + phone data. Created by Abhishek Kaushal.")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--data-dir", default=os.environ.get("LIFELENS_DATA", "data"),
                   help="where your CSV data lives (default: ./data, or $LIFELENS_DATA)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("demo", help="generate synthetic sample data")
    s.add_argument("--days", type=int, default=60)
    s.set_defaults(fn=cmd_demo)

    s = sub.add_parser("import", help="import data from a file")
    s.add_argument("kind", choices=["daily", "apps", "apple-health"])
    s.add_argument("path")
    s.add_argument("--map", nargs="*", metavar="FIELD=COLUMN", help="custom column mapping for 'daily'")
    s.add_argument("--since", help="apple-health only: YYYY-MM-DD")
    s.set_defaults(fn=cmd_import)

    sub.add_parser("today", help="daily brief: score, focus habit, targets").set_defaults(fn=cmd_today)
    s = sub.add_parser("habits", help="good/bad habits and top apps")
    s.add_argument("--window", type=int, default=30)
    s.set_defaults(fn=cmd_habits)
    sub.add_parser("insights", help="patterns in your data").set_defaults(fn=cmd_insights)
    s = sub.add_parser("score", help="daily score table")
    s.add_argument("--window", type=int, default=14)
    s.set_defaults(fn=cmd_score)
    s = sub.add_parser("report", help="write the HTML dashboard")
    s.add_argument("--out", default="reports/report.html")
    s.add_argument("--window", type=int, default=30)
    s.set_defaults(fn=cmd_report)
    s = sub.add_parser("ask", help="ask the AI coach a question (needs ANTHROPIC_API_KEY)")
    s.add_argument("question", nargs="+")
    s.set_defaults(fn=cmd_ask)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    args.fn(args)
    return 0
