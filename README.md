# Nolon Leaderboard Template

[![CI](https://github.com/linhay/nolon-leaderboard-template/actions/workflows/ci.yml/badge.svg)](https://github.com/linhay/nolon-leaderboard-template/actions/workflows/ci.yml)
[![Pages](https://img.shields.io/badge/pages-live-0a7ea4)](https://linhay.github.io/nolon-leaderboard-template/)

Fork this repository on GitHub or GitLab to run an independent token leaderboard site.

## What this template includes

- Static leaderboard website (`web/`)
- Top 5 token trend chart (`7d / 14d / 30d / 90d`)
- Submission storage (`data/submissions/`)
- CI audit scripts for PR/MR (`scripts/`)
- Snapshot builder (`data/snapshots/latest.json`)
- GitHub Pages and GitLab Pages pipelines

## Submission contract

Each submission file lives under `data/submissions/<userId>/<timestamp>.json`.

Required fields:

- `userId`
- `username`
- `submittedAt` (ISO8601)
- `clientVersion`
- `points[]`

`points` item fields:

- `date` (`YYYY-MM-DD`)
- `tool` (string, e.g. `codex`, `gemini`)
- `totalTokens`
- `inputTokens`
- `outputTokens`
- `cacheReadTokens`

## Local development

```bash
cd projects/leaderboard-template
python3 -m unittest discover -s scripts/tests -v
node --test web/tests/*.test.js
python3 scripts/validate_all_submissions.py .
python3 scripts/build_snapshot.py .
python3 scripts/check_screenshot_regression.py screenshots
python3 scripts/capture_mock_screenshots.py . --date 20260303
python3 scripts/build_site_bundle.py .
```

Then serve `.site` with any static server.

## CI behavior

- PR/MR: validate submissions + build snapshot + fail on snapshot drift
- `main`: same audit + publish static site

## Notes

- Submission does not include platform fields.
- Tool rankings are generated per `points[].tool`.
- Alias mapping can be configured in `config/tool_aliases.json`.
- Snapshot includes `timeseries` for trend rendering:
  - `timeseries.overall`
  - `timeseries.byTool.<tool>`
  - dataset shape: `{ dates: string[], users: [{ userId, username, displayName, values: number[] }] }`

- Top 5 trend chart supports hover tooltip and 7d/14d/30d/90d window switching.
- Screenshot regression check: `python3 scripts/check_screenshot_regression.py screenshots`

- `screenshots/` and `.local/` are git-ignored for local visual regression artifacts.
