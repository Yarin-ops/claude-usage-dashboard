# Comparison with iftahs/claude-dashboard

[iftahs/claude-dashboard](https://github.com/iftahs/claude-dashboard) is the most visible alternative in this space and a clear inspiration for the activity heatmap and the 5-hour block ring. This page is a fair, side-by-side comparison so you can pick the one that fits your setup. No "ours is better" — both are good at what they aim at.

## TL;DR

- **iftahs** if you want a live web app feel with a backend, are comfortable with Node + npm or Docker, and want it always-on.
- **this one** if you want a single HTML file you double-click, prefer reading the whole codebase before running it, or care about the "Pay vs Use" framing.

## Side by side

| | iftahs/claude-dashboard | claude-usage-dashboard (this repo) |
|---|---|---|
| **Stack** | React + Vite + Express (Node 18+, TypeScript) | Single HTML + Python 3 stdlib |
| **Run** | `npm install && npm run dev` or Docker | `python3 analyzer.py && open index.html` |
| **Always-on option** | Docker container with `restart: unless-stopped` | Run `analyzer.py --watch` in a terminal |
| **5-hour block ring** | ✅ | ✅ |
| **Activity heatmap** | ✅ (18 weeks) | ✅ (18 weeks) |
| **Tool usage breakdown** | ✅ | ✅ (with MCP names shortened) |
| **Live refresh** | ✅ (backend polling) | ✅ (HTML polls JSON every 30s) |
| **Weekly trends with WoW delta** | ✅ (range selector 1-4 wk) | ✅ (delta chip on daily chart) |
| **Pay vs Use framing** | ❌ | ✅ |
| **Editable subscriptions / API connections** | ❌ | ✅ (saves to localStorage) |
| **Reality-check banner** | ❌ | ✅ |
| **Monthly trend** | ❌ | ✅ |
| **Top projects bar list** | ❌ | ✅ |
| **Recent sessions table** | ❌ | ✅ |
| **English + Hebrew i18n with RTL** | ❌ | ✅ |
| **Settable personal cap** | ✅ (limits panel) | ✅ (limits popover) |
| **Dependencies installed** | ~150 npm packages | 0 (stdlib only) |
| **Open offline / from a USB stick** | Requires Node | Yes |
| **Lines of code** | TS app (multi-file) | ~2700 lines HTML + ~400 lines Python |
| **License** | MIT | MIT |

## Where iftahs is better

- **Polish in the chart layer** — Recharts gives smooth axes, tooltips, animations that Chart.js doesn't match by default. The weekly stacked bar with model breakdown is genuinely nicer there.
- **Backend-driven freshness** — the Express server scans on every poll, so data is always one HTTP call away from current. No external `--watch` process needed.
- **Type safety** — TypeScript will catch a class of bugs that a plain JS file won't.

## Where this one is better

- **Trust surface** — the entire system is two files you can read end to end. No node_modules to audit.
- **Setup time** — clone, run one Python command, open in browser. No build, no install, no port to remember.
- **Pay vs Use framing** — the headline framing puts real cash on one side and real usage on the other instead of leading with "look how much you saved on cache." That's the difference in editorial stance, not features.
- **i18n with RTL out of the box** — Hebrew works correctly including layout direction, which web apps usually retrofit awkwardly.
- **More usage angles** — monthly trend, top projects, recent sessions, editable subscription costs. Closer to a personal-finance view of "what is Claude actually costing me" than a pure rate-limit watcher.

## Why they exist together

The two repos optimize for different mental models:

- iftahs: *I want a live operations dashboard for my rate-limit window.*
- this one: *I want a quarterly review of my Claude relationship.*

Both are correct. Pick the one that matches the question you keep asking yourself.

## Credit

Two ideas in this repo originate from iftahs's earlier work and are kept here with a tip of the hat:

- The **GitHub-style activity heatmap** layout (18-week, 7-day grid, sqrt-scaled intensity).
- The **effective tokens** metric for the 5-hour block (input + output + cache_write, excluding cache_read).

Everything else evolved independently. If you're starting fresh, look at both — they're small enough to skim in 20 minutes each.
