# LifeLens

[![tests](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml) ![python](https://img.shields.io/badge/python-3.10%2B-blue) ![license](https://img.shields.io/badge/license-MIT-green)

*By Abhishek Kaushal*

**A local-first AI-assistant-style analyzer for your daily life.** Feed it your smartwatch and phone data
and it tells you how your days are really going: a daily performance score, your good and bad habits,
patterns hidden in your own data, and a short coaching brief each day.

![report preview](docs/report-preview.png)
*(preview built from synthetic demo data)*

## What it does

| You get | How |
|---|---|
| **Daily performance score (0-100)** | Activity 30%, Sleep 30%, Recovery 20%, Digital wellbeing 20% - judged against *your own* baseline |
| **Phone usage analysis** | Screen time, unlocks, late-night use, per-app and per-category (social, video, games...) |
| **Smartwatch activity & health record** | Steps, active minutes, workouts, calories, sleep, bedtime, resting HR, HRV, SpO2 |
| **Habit detection** | 7 bad habits (late bedtime, night scrolling, social binges, sedentary days...) and 5 good ones, with frequency, trend and streaks |
| **Personal insights** | e.g. "On nights after heavy late-night phone use, your sleep averages 6.4h vs 7.5h" |
| **Assistant brief** | One focus habit for the week, a concrete tip, and today's targets |
| **Optional LLM coach** | `lifelens ask "why am I tired in the afternoons?"` (opt-in, aggregates only) |
| **HTML dashboard** | Performance chart, steps, sleep, screen time, bedtime, habits, top apps - self-contained, works offline |

## Quick start (no dependencies, Python 3.10+)

```bash
git clone <your-repo-url> && cd lifelens
export PYTHONPATH=src            # or: pip install -e .

python -m lifelens demo          # synthetic sample data, to try it out
python -m lifelens today         # your daily brief
python -m lifelens habits        # good / bad habits + top apps
python -m lifelens insights      # patterns in your data
python -m lifelens report        # -> reports/report.html
```

## Use your own data

```bash
python -m lifelens import apple-health export.xml      # Apple Watch / iPhone
python -m lifelens import daily fitbit_or_garmin.csv    # Fitbit, Garmin, Google Fit, Samsung...
python -m lifelens import apps usage.csv                # phone app usage (date,app,minutes)
```
See [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) for how to export from each device. Android/iOS
screen-time has no official export, so it uses a simple CSV format.

## Privacy

Your data stays in `./data/` (git-ignored). No accounts, telemetry or cloud. The one optional network
feature (`ask`) sends only an aggregate summary and only if you set `ANTHROPIC_API_KEY`.
Details: [docs/PRIVACY.md](docs/PRIVACY.md).

## How the assistant works

1. **Importers** normalise any source into one `Day` record per date.
2. **Scoring** compares each day with your own medians (so a 5,000-step day means different things for different people).
3. **Habit rules** (`analysis/habits.py`) are plain, editable thresholds - tune them to your life.
4. **Insights** run lagged correlations (e.g. tonight's phone use vs tomorrow's sleep) and only report
   relationships with 14+ days of data and |r| >= 0.3. They are tendencies, not proof of cause.
5. **Assistant** turns it all into a brief; optionally an LLM answers free-form questions from the summary.

## Develop

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Roadmap
- Live sync: Fitbit Web API, Google Health Connect (Android companion), Garmin Connect
- Android/iOS companion for automatic screen-time capture
- Weekly email/notification digest, goals and custom habit rules in a config file
- Sleep-consistency and workout-recovery scoring

## Disclaimer
LifeLens provides lifestyle suggestions, not medical advice or diagnosis.

## Author
Created by **Abhishek Kaushal**.

## License
MIT, see [LICENSE](LICENSE).
