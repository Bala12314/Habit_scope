# Privacy

Health and phone-usage data is sensitive. LifeLens is built to keep it yours.

- **Local-first.** All data is stored as CSV in `./data/` (git-ignored) on your machine. The reports are
  static HTML with no scripts and no network calls.
- **No telemetry, no accounts, no cloud.**
- **The only network feature is opt-in:** `lifelens ask` sends a *compact aggregate summary*
  (medians, habit counts, top apps) - never raw daily rows - to the Anthropic API, and only if you set
  `ANTHROPIC_API_KEY`. Run `python -c "from lifelens import assistant,storage;import json;print(json.dumps(assistant.build_context(storage.load('data')),indent=2))"`
  to see exactly what would be sent.
- **Never commit your data.** `.gitignore` excludes `data/`, `reports/` and Health `*.xml` exports.
- **Not medical advice.** Scores and habit rules are lifestyle heuristics. Consult a clinician for health concerns.
