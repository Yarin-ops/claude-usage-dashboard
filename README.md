# Claude Usage Dashboard

A **local, no-API, no-account** dashboard for your [Claude Code](https://claude.com/claude-code) usage. Reads the JSON logs Claude Code already writes to `~/.claude` and turns them into a clear, beautiful view of what you actually pay vs. what you actually use.

One HTML page and one Python script. Opens with a double-click. Fonts, charts and icons ship in the repo, so it makes no network calls and works offline.

![Pay vs Use headline, the 5-hour orbit, and the activity heatmap](screenshots/01-hero.png)

## Why another one?

There are other Claude usage viewers out there. They all answer the same question: *how many tokens did I burn this week*. None of them answer the question I actually care about: **am I getting my money's worth?**

This one starts there. The top of the page is one sentence: **You pay $100. You use $319.**
- **What you pay** — your real subscriptions + any pay-per-use APIs you list, with prices you edit inline. Real cash out.
- **What you use** — the same month's usage at API rates (what it would cost on pay-as-you-go), clearly labeled as a reference, not a savings claim. Next to it: hours active, days, messages, and your real cost per active hour.

Everything else flows from that framing.

## Features

- **5-hour orbit** — effective tokens in the last 5 hours against a personal cap you set, and it says so when you go over
- **Activity heatmap** — 26 weeks × 7 days, GitHub-style intensity grid colored by effective tokens
- **Pay vs Use** — your subscriptions on one side, your real usage on the other, no marketing spin
- **Tool usage breakdown** — which tools (Bash, Read, Edit, MCP servers…) you call most, every call counted
- **Daily activity** — last 60 days with a hours / messages / API-equiv $ toggle and a week-over-week delta chip
- **Model mix** — message share across Fable / Opus / Sonnet / Haiku, priced per exact model version
- **Monthly trend** — active hours per month
- **Top projects** — bar list, where your Claude time goes
- **Recent sessions** — last 10
- **Editable subscriptions + API connections** — prices live in localStorage on your machine only
- **i18n** — full English + Hebrew with RTL layout
- **Dark / light theme** — auto-detected from your OS, toggleable
- **Live auto-refresh** — polls the data file every 30 seconds; pause when the tab is hidden
- **Pure static** — no build step, no npm, no CDN

> **Token accounting:** "effective tokens" = `input + output + cache_write`. Cheap cache reads are excluded because they don't count toward rate limits.

![Light theme: the heatmap and the Pay vs Use ledger](screenshots/02-light.png)

![Hebrew and RTL: daily activity, tools and projects](screenshots/03-hebrew.png)

## Try it without your own data

Want to see the dashboard before running anything against your `~/.claude`?

Open `index.html?demo`, or click **See it with demo data** on the first-run screen. Nothing is copied or overwritten.

You'll see six months of synthetic activity across six example projects, clearly marked as demo data. See `examples/README.md` for details.

## Quick start

You need Python 3 (any version since 3.8). That's it.

```bash
git clone https://github.com/Yarin-ops/claude-usage-dashboard.git
cd claude-usage-dashboard

# Generate the data file from your local Claude Code logs.
python3 analyzer.py

# Open the dashboard.
open index.html      # macOS
xdg-open index.html  # Linux
start index.html     # Windows
```

The dashboard reads the data file next to it. No server, no build, no install.

### Live mode

If you want the dashboard to update in real time as you use Claude Code:

```bash
python3 analyzer.py --watch
# or with a custom interval (seconds, min 5):
python3 analyzer.py --watch --interval=15
```

Leave that running in a terminal. The dashboard polls the JSON every 30 seconds and re-renders only when `generated_at` changes. A small green dot pulses next to "Generated" to confirm the loop is live.

## Configuring

### Your subscriptions

Open `index.html` and find the `SUBSCRIPTIONS` array near the top of the `<script>` block. Edit the rows to match what you actually pay each month:

```js
const SUBSCRIPTIONS = [
  { id: 'claude-max', name_en: 'Claude Max', name_he: 'Claude Max',
    vendor: 'Anthropic', usd: 100,
    what_en: 'Claude Code + Claude.ai', what_he: 'Claude Code + Claude.ai' },
];
```

You can also edit the price inline in the dashboard — click any `$XX` value next to a subscription and type a new amount. It saves to `localStorage` on your machine only.

### Pay-per-use API connections

If you also pay Anthropic / OpenAI / others directly (e.g., for a deployed agent), list them in the `API_CONNECTIONS` array. Prices start blank; type the real amount next to each one from the vendor's billing page. The `billing_url` you set on each row becomes a "check billing" link inside the dashboard.

### Personal 5-hour cap

Click the **Cap** button next to the 5-hour title. Pick a preset (1M / 2M / 4M / 8M / 16M effective tokens) or enter your own. The orbit fills based on this cap. Saved to `localStorage`.

### Claude data folder

By default the analyzer reads `~/.claude`. Override with `CLAUDE_DIR`:

```bash
CLAUDE_DIR=/path/to/.claude python3 analyzer.py
```

## What this dashboard can and can't show

It reflects **only** what Claude Code records locally in `~/.claude/projects/**/*.jsonl`. Two things are deliberately not shown because they don't live in those logs:

- **Exact rate-limit reset time and remaining quota** — those live in Anthropic API response headers, which Claude Code doesn't persist. Any countdown would be a guess.
- **Claude.ai web usage** — server-side per-conversation, never written to `~/.claude`.

You can set a personal cap in the 5-hour block panel to get a "% used" gauge — it compares measured effective tokens against the number you enter.

## Acknowledgments

Inspired by [iftahs/claude-dashboard](https://github.com/iftahs/claude-dashboard) — same underlying idea (a local viewer over `~/.claude` logs), different framing and different stack.

Where this one diverges:
- **Pay vs Use** headline framing — real cash + real usage side by side, with editable subscription pricing built in
- **Static HTML + Python**, no Node.js, no React, no build step
- **i18n EN/HE with RTL** — built in, not bolted on
- **Tool usage** card aggregates MCP server tools too, with shortened pretty names

Pick the one that fits how you like to run things.

## Project layout

```
.
├── index.html                  The dashboard (HTML + CSS + JS inline)
├── vendor/                     Pinned Chart.js and fonts, so nothing loads from a CDN
├── analyzer.py                 Reads ~/.claude logs → writes claude-usage-data.json
├── examples/                   Synthetic demo data + the generator that builds it
├── tests/                      Analyzer tests (`python3 -m unittest discover -s tests`)
├── docs/                       Pricing math, architecture, comparison with iftahs
├── screenshots/                README screenshots (light, dark, hebrew, heatmap)
├── .github/
│   ├── ISSUE_TEMPLATE/         Bug + feature request forms
│   └── workflows/              CI (Python lint + demo-data smoke test)
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE                     MIT
└── README.md                   This file
```

## Further reading

- [Pricing & cost math](docs/pricing.md) — exactly how each message becomes a dollar number.
- [Architecture](docs/architecture.md) — the three pieces, the data contract, why no server.
- [Comparison with iftahs/claude-dashboard](docs/comparison-with-iftahs.md) — fair side-by-side, pick the one that fits.
- [Contributing](CONTRIBUTING.md) — what's in scope and what isn't.
- [Changelog](CHANGELOG.md) — what's changed across releases.

## Contributing

Open an [issue](https://github.com/Yarin-ops/claude-usage-dashboard/issues) for bugs or feature ideas. See [CONTRIBUTING.md](CONTRIBUTING.md) for scope rules. PRs welcome.

## License

[MIT](LICENSE) — free to use, modify, and distribute.
