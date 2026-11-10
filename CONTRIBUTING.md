# Contributing

Thanks for helping! LifeLens is standard-library only; please keep it dependency-free.

1. Fork and create a branch.
2. Run the tests: `PYTHONPATH=src python -m unittest discover -s tests -v`
3. Add a test for any new behaviour (importer, habit rule, score change).
4. Open a pull request describing what and why.

Good first contributions: a new importer (Fitbit/Garmin API, Health Connect), new habit rules in
`src/lifelens/analysis/habits.py`, or better report charts.

**Never commit real health data.** `data/`, `reports/` and Health `*.xml` are git-ignored; keep it that way.
