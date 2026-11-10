# Getting your data into LifeLens

LifeLens reads two simple local CSV files (`data/daily_metrics.csv`, `data/app_usage.csv`).
Phone and watch vendors don't offer one universal API, so there are three routes.

## 1. Apple Watch / iPhone health data
Health app -> profile picture -> **Export All Health Data** -> unzip -> `export.xml`.

```bash
python -m lifelens import apple-health export.xml --since 2026-01-01
```
Imports steps, active energy, exercise minutes, heart rate, resting HR, HRV, SpO2 and sleep.

## 2. Fitbit / Garmin / Google Fit / Samsung Health / anything with CSV export
Use the vendor's data export (Fitbit: *Settings -> Data Export*, Google: *Takeout*, Garmin: *Connect -> Reports*).
Column names are matched against common aliases (`Step Count`, `Minutes Asleep`, `Resting Heart Rate`, ...).

```bash
python -m lifelens import daily my_export.csv
python -m lifelens import daily odd.csv --map steps="Total Steps" resting_hr="RHR (bpm)"
```
Supported fields: `steps, active_minutes, workout_minutes, calories, sleep_hours | sleep_minutes,
bedtime, wake, resting_hr, avg_hr, hrv, spo2, screen_min, unlocks, night_screen_min`.

## 3. Phone usage (screen time, apps, pickups)
Android Digital Wellbeing and iOS Screen Time have **no official export**. Options:
- Copy the numbers into the neutral CSV below by hand once a day (30 seconds), or
- Use an automation app (Tasker / Shortcuts) or a usage-stats app that exports CSV, then convert to:

```csv
date,app,minutes,night_minutes
2026-11-09,Instagram,74,22
2026-11-09,YouTube,51,8
```
```bash
python -m lifelens import apps usage.csv
```
`night_minutes` (optional) = minutes after 23:00. Totals (`screen_min`) are derived from the apps.

## Live sync (roadmap)
Fitbit Web API, Google Health Connect (Android companion app), and Garmin Connect each need an
OAuth app or on-device bridge. They are listed in the README roadmap; importers above are the stable path today.
