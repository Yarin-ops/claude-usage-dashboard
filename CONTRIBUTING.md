# Contributing

Thanks for being interested. This project is small on purpose, so the bar for changes is "does it make the existing thing clearer or more honest?" rather than "does it add a feature?"

## Before opening a PR

1. **Read the [architecture doc](docs/architecture.md).** It explains why the system is two files (Python + HTML) and what that constraint costs us. Most "improvements" that break that constraint will be declined.
2. **Open an issue first** for anything bigger than a typo or a one-line fix. Saves you time if the change isn't going to land.
3. **Check the [comparison with iftahs](docs/comparison-with-iftahs.md).** If your idea is fundamentally about a live web app with a backend, that other project is the better home and you should contribute there.

## Scope rules

What this project will keep doing:

- **Single HTML file** — no separate `.css`, no separate `.js`, no build step. Inline everything.
- **One Python script** — standard library only. No `pip install`. Anything that needs a package goes in a different project.
- **No network calls at runtime** — the dashboard ships its data file via filesystem, not HTTP.
- **No telemetry** — nothing this project does should phone home, ever.

What it will not become:

- A web service with login.
- A SaaS.
- A React app.
- A CLI that prints reports.

## Local setup

```bash
git clone https://github.com/Yarin-ops/claude-usage-dashboard.git
cd claude-usage-dashboard
python3 analyzer.py            # generates claude-usage-data.json
open index.html                # or xdg-open / start
```

For watch mode:

```bash
python3 analyzer.py --watch
```

## Code style

- **Python** — PEP 8, max line length 120. Use `flake8` (the CI runs it). No external linters or formatters required.
- **HTML/CSS/JS** — keep CSS in the existing `<style>` block, JS in the existing `<script>` block. New components follow the existing visual language (CSS variables for colors, Heebo font, Lucide icons).
- **No emojis in code.** Lucide icons only.
- **Hebrew strings** live in the same `I18N` table as English — don't fork the table.

## Commits

- Conventional-ish: a short subject line in lowercase ("add tool breakdown", "fix wow chip sign"). One topic per commit.
- Reference an issue number when one exists: `add wow chip to daily card (#12)`.

## Things that need help

- **More screenshots** in `screenshots/` — dark mode, Hebrew mode, light mode, mobile.
- **A weekly stacked bar chart** — model breakdown per day for a selectable 1-4 week range. Data is already in `by_day[].by_model`; just needs a Chart.js stacked dataset and a range toggle.
- **Tests for `analyzer.py`** — there are none right now. A tiny pytest suite that runs against `examples/demo-data.json`'s shape would be welcome.
- **More languages** — adding a third language to the `I18N` table is mechanical but tedious. PRs welcome for Arabic, Russian, Spanish, etc.

## License

By contributing, you agree that your contributions will be licensed under the MIT License, the same as the rest of the project.
