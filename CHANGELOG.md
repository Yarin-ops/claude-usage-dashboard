# Changelog

All notable changes to this project will be documented in this file. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] — 2026-05-30

Initial public release.

### Added
- `analyzer.py` — scans `~/.claude/projects/**/*.jsonl`, dedupes by message id, computes per-message cost using current Anthropic pricing (Opus / Sonnet / Haiku, including 5m and 1h cache write multipliers and 0.10× cache read).
- `analyzer.py --watch [--interval=N]` — re-runs every N seconds (default 30) so the dashboard stays live.
- `index.html` — single-file dashboard with:
  - **Pay vs Use** headline framing — real subscriptions + editable API connection prices on one side, real usage hours on the other.
  - **Current 5-hour block** ring with a settable personal token cap (saved in `localStorage`).
  - **Activity heatmap** — 18-week × 7-day grid, gradient-colored by effective tokens.
  - **Tool usage breakdown** — top 12 tools lifetime with MCP names shortened.
  - **Daily activity chart** — last 60 days with hours / messages / API-equivalent $ toggle, plus a week-over-week delta chip.
  - **Model mix** — token share doughnut across Opus / Sonnet / Haiku.
  - **Monthly trend** — active hours per month.
  - **Top projects** bar list.
  - **Recent sessions** table.
  - **Reality-check banner** — plain-English read on what your spend means.
- **Live polling** — dashboard polls `claude-usage-data.json` every 30 seconds and re-renders only when `generated_at` changes.
- **i18n** — full English + Hebrew with RTL layout direction.
- **Theme** — auto-detected dark / light with explicit toggle.
- `examples/demo-data.json` + `examples/generate_demo_data.py` — synthetic data for previewing the dashboard without local logs.
- Documentation under `docs/`: `pricing.md`, `architecture.md`, `comparison-with-iftahs.md`.
- GitHub Actions workflow `python-lint.yml` for Python lint and demo-data smoke test.

### Credit
The activity heatmap layout and the effective-tokens metric for the 5-hour block were inspired by [iftahs/claude-dashboard](https://github.com/iftahs/claude-dashboard). See `docs/comparison-with-iftahs.md` for a fair side-by-side.

[Unreleased]: https://github.com/Yarin-ops/claude-usage-dashboard/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Yarin-ops/claude-usage-dashboard/releases/tag/v0.1.0
