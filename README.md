# Nolon Leaderboard Template

Fork this repository on GitHub or GitLab to run an independent token leaderboard site.

## What this template includes

- Static leaderboard website (`web/`)
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
python3 scripts/validate_all_submissions.py .
python3 scripts/build_snapshot.py .
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
