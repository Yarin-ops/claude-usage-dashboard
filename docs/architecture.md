# Architecture

A one-page explanation of how the three moving pieces fit together and why the dashboard is designed as a static file rather than a web app.

## The shape

```
┌────────────────────────────────────────────────────────────┐
│  ~/.claude/projects/**/*.jsonl                             │
│  ──────────────────────────────                            │
│  Claude Code writes one .jsonl per session here.           │
│  Each line is a JSON record. Assistant messages carry      │
│  a usage payload with token counts and model id.           │
└──────────────────────┬─────────────────────────────────────┘
                       │
                       │  python3 analyzer.py
                       ▼
┌────────────────────────────────────────────────────────────┐
│  claude-usage-data.json  (+ .js fallback)                  │
│  ────────────────────────────────                          │
│  A single compact JSON summary: totals, by_day,            │
│  by_month, by_model, by_project, by_tool,                  │
│  current_block, recent_sessions.                           │
│  Written next to index.html.                               │
└──────────────────────┬─────────────────────────────────────┘
                       │
                       │  fetch (polled every 30s)
                       ▼
┌────────────────────────────────────────────────────────────┐
│  index.html                                                │
│  ───────────                                               │
│  Single HTML file. CSS + JS inline. Chart.js + Lucide      │
│  pulled from CDN. Renders the JSON into the dashboard.     │
└────────────────────────────────────────────────────────────┘
```

That's the whole system. Three files, one direction.

## Why static instead of a server

The very first version was sketched as Express + React + a backend route that scans the logs on demand. It was thrown out for three reasons:

1. **Trust** — a dashboard that watches your activity should be small enough to read in 20 minutes. Single HTML + one Python script clears that bar. A server with dependencies does not.
2. **Friction** — `python3 analyzer.py && open index.html` is one line in a README. `npm install && npm run dev` is a setup ritual, especially on a fresh machine.
3. **Portability** — the dashboard works offline, on an air-gapped laptop, opened from a USB stick. A server-bound version doesn't.

The cost of being static is that the data file only refreshes when you re-run the analyzer. The dashboard solves this with a `--watch` mode on the analyzer (re-runs every N seconds) plus 30-second polling on the HTML side. Trade is worth it.

## The analyzer

`analyzer.py` is one file with one entry point. It:

1. Walks `~/.claude/projects/**/*.jsonl` (or whatever `CLAUDE_DIR` points to).
2. For each line: parses JSON, keeps only `type=="assistant"` records that have a `usage` block.
3. Dedupes across files using `message.id`.
4. Per record: looks up the model bucket, computes cost via the pricing table, scans the message's `content[]` blocks for `tool_use` entries to count tool invocations.
5. Aggregates into a stack of buckets: by day, by month, by model, by project, by tool, by session.
6. Computes the **current 5-hour block** by including only records whose timestamp is within `now − 5h`.
7. Writes the result as JSON next to itself.

No external dependencies. Standard library only.

## The dashboard

`index.html` is a single file containing:

- **Inline CSS** — design tokens at the top, then component styles. Light + dark theme via `data-theme` attribute on `<html>`.
- **i18n table** — English + Hebrew translations in one `I18N` object. The direction (`dir="ltr"` / `"rtl"`) is set at the document root.
- **Configuration** — `SUBSCRIPTIONS` and `API_CONNECTIONS` arrays. Users edit these (or set values inline in the dashboard, which save to `localStorage`).
- **Data loader** — `fetch('claude-usage-data.json')` with a cache-busting timestamp. Falls back to `<script src="claude-usage-data.js">` if the file is opened from `file://` (where browsers block sibling `fetch`).
- **Render layer** — `render(data)` builds the HTML in one pass, then `renderCharts(data)` initializes Chart.js instances on the four `<canvas>` elements.
- **Polling loop** — `setInterval(pollData, 30_000)`; re-renders only when `generated_at` changes.

The single-file design is enforced. CSS that's not in `<style>` and JS that's not in `<script>` doesn't ship.

## Data contract

The JSON file written by the analyzer has a stable top-level shape:

| Key | Type | Notes |
|---|---|---|
| `generated_at` | ISO timestamp | When the analyzer last ran. Polling uses this to detect changes. |
| `totals` | object | Lifetime input/output/cache token counts + cost breakdown + messages. |
| `pricing` | object | The price table that was used. |
| `by_day` | array | One entry per day. Includes `effective_tokens` and `by_model` per day. |
| `by_month` | array | One entry per month. |
| `by_model` | array | Lifetime model totals. |
| `by_project` | array | Lifetime per-project totals, sorted by cost. |
| `by_tool` | array | Lifetime per-tool invocation counts, sorted descending. |
| `current_block` | object | The active 5-hour window — start time, effective tokens, cost, messages, top tools. |
| `recent_sessions` | array | Last 40 sessions, most recent first. |
| `files_scanned` | number | Diagnostic. |

If you fork the dashboard and change any of these names, update both `analyzer.py` and the matching field in the render functions in `index.html`.
