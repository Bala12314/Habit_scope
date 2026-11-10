import tempfile
import textwrap
import unittest
from datetime import date, timedelta
from pathlib import Path

from lifelens import assistant, report, storage
from lifelens.analysis import habits as H
from lifelens.analysis import insights as I
from lifelens.analysis import score as S
from lifelens.ingest import apple_health, csv_import, sample
from lifelens.models import Day, categorize, fmt_clock, parse_clock


class Models(unittest.TestCase):
    def test_clock(self):
        self.assertEqual(parse_clock("23:30"), 23.5)
        self.assertEqual(parse_clock("00:45"), 24.75)
        self.assertEqual(parse_clock("2024-01-01 01:00:00"), 25.0)
        self.assertIsNone(parse_clock("nonsense"))
        self.assertEqual(fmt_clock(24.5), "00:30")

    def test_category(self):
        self.assertEqual(categorize("Instagram"), "social")
        self.assertEqual(categorize("Some Random App"), "other")


class Scoring(unittest.TestCase):
    def test_great_day_beats_bad_day(self):
        base = {"resting_hr": 60, "hrv": 50}
        good = Day(date(2026, 1, 1), steps=11000, active_minutes=45, sleep_hours=8, bedtime_h=23,
                   resting_hr=58, hrv=55, screen_min=150, unlocks=60, night_screen_min=0)
        bad = Day(date(2026, 1, 2), steps=2000, active_minutes=5, sleep_hours=4.5, bedtime_h=26,
                  resting_hr=68, hrv=35, screen_min=500, unlocks=200, night_screen_min=90)
        g, b = S.score_day(good, base), S.score_day(bad, base)
        self.assertGreater(g.total, 90)
        self.assertLess(b.total, 30)

    def test_missing_components_renormalise(self):
        sc = S.score_day(Day(date(2026, 1, 1), steps=10000), {})
        self.assertEqual(sc.total, 100)
        self.assertEqual(list(sc.components), ["activity"])
        self.assertIsNone(S.score_day(Day(date(2026, 1, 1)), {}).total)


class Habits(unittest.TestCase):
    def _days(self, n, **kw):
        end = date(2026, 3, 1)
        return [Day(date=end - timedelta(days=n - 1 - i), **kw) for i in range(n)]

    def test_detects_and_streaks(self):
        days = self._days(10, steps=9000, bedtime_h=25.0)
        stats = {s.rule.id: s for s in H.evaluate(days)}
        self.assertEqual(stats["late_bedtime"].hits, 10)
        self.assertTrue(stats["late_bedtime"].established)
        self.assertEqual(stats["steps_goal"].current_streak, 10)
        self.assertNotIn("sedentary", [s.rule.id for s in H.bad_habits(list(stats.values()))])

    def test_unknown_data_is_skipped(self):
        ids = [s.rule.id for s in H.evaluate(self._days(5, steps=100))]
        self.assertIn("sedentary", ids)
        self.assertNotIn("late_bedtime", ids)


class Insights(unittest.TestCase):
    def test_finds_planted_relationship(self):
        days = sample.generate(45, end=date(2026, 3, 1))
        texts = " ".join(i.text for i in I.find_insights(days))
        self.assertIn("late-night phone use", texts)

    def test_too_little_data(self):
        self.assertEqual(I.find_insights(sample.generate(5)), [])


class Importers(unittest.TestCase):
    def test_daily_csv_aliases(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t, "x.csv")
            p.write_text("Date,Step Count,Minutes Asleep,Resting Heart Rate,Bedtime\n"
                         "2026-01-01,\"8,500\",420,61,23:45\n"
                         "garbage,1,1,1,1\n"
                         "01/02/2026,100,,,00:15\n")
            days, skipped = csv_import.import_daily_csv(p)
        self.assertEqual(skipped, 1)
        self.assertEqual(days[0].steps, 8500)
        self.assertEqual(days[0].sleep_hours, 7.0)
        self.assertEqual(days[0].bedtime_h, 23.75)
        self.assertEqual(days[1].bedtime_h, 24.25)

    def test_app_usage_csv(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t, "a.csv")
            p.write_text("date,app,minutes\n2026-01-01,Instagram,60\n2026-01-01,YouTube,30\n")
            days, _ = csv_import.import_app_usage_csv(p)
        self.assertEqual(days[0].screen_min, 90)

    def test_apple_health(self):
        xml = textwrap.dedent("""\
            <HealthData>
             <Record type="HKQuantityTypeIdentifierStepCount" value="3000" startDate="2026-01-02 08:00:00 +0530" endDate="2026-01-02 09:00:00 +0530"/>
             <Record type="HKQuantityTypeIdentifierStepCount" value="2500" startDate="2026-01-02 12:00:00 +0530" endDate="2026-01-02 13:00:00 +0530"/>
             <Record type="HKQuantityTypeIdentifierRestingHeartRate" value="60" startDate="2026-01-02 00:00:00 +0530" endDate="2026-01-02 23:59:00 +0530"/>
             <Record type="HKCategoryTypeIdentifierSleepAnalysis" value="HKCategoryValueSleepAnalysisAsleepCore" startDate="2026-01-01 23:30:00 +0530" endDate="2026-01-02 06:30:00 +0530"/>
             <Record type="HKCategoryTypeIdentifierSleepAnalysis" value="HKCategoryValueSleepAnalysisInBed" startDate="2026-01-01 23:00:00 +0530" endDate="2026-01-02 07:00:00 +0530"/>
            </HealthData>""")
        with tempfile.TemporaryDirectory() as t:
            p = Path(t, "export.xml")
            p.write_text(xml)
            days = apple_health.import_apple_health(p)
        d = days[0]
        self.assertEqual(d.steps, 5500)
        self.assertEqual(d.resting_hr, 60)
        self.assertAlmostEqual(d.sleep_hours, 7.0)
        self.assertEqual(d.bedtime_h, 23.5)


class StorageAndOutputs(unittest.TestCase):
    def test_roundtrip_and_merge(self):
        days = sample.generate(20, end=date(2026, 3, 1))
        with tempfile.TemporaryDirectory() as t:
            storage.save(t, days)
            back = storage.load(t)
            self.assertEqual(len(back), 20)
            self.assertEqual(back[-1].steps, days[-1].steps)
            self.assertEqual(set(back[-1].apps), set(days[-1].apps))
            merged = storage.merge(back, [Day(date=back[-1].date, steps=1)])
            self.assertEqual(merged[-1].steps, 1)
            self.assertEqual(merged[-1].sleep_hours, back[-1].sleep_hours)

    def test_brief_report_and_context(self):
        days = sample.generate(30, end=date(2026, 3, 1))
        self.assertIn("score", assistant.daily_brief(days))
        self.assertIn("No data", assistant.daily_brief([]))
        ctx = assistant.build_context(days)
        self.assertIn("bad_habits", ctx)
        html = report.render(days)
        self.assertTrue(html.startswith("<!doctype html>"))
        self.assertIn("Performance score", html)


if __name__ == "__main__":
    unittest.main()
