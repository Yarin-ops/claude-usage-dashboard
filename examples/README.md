# Examples

## `demo-data.json`

A synthetic, anonymized dataset shaped exactly like what `analyzer.py` produces. Use it to see the dashboard without running the analyzer against your own logs.

### How to use

```bash
# From the repo root:
cp examples/demo-data.json claude-usage-data.json
open index.html  # or xdg-open / start
```

You'll see ~70 days of synthetic activity with a realistic mix of Opus / Sonnet / Haiku, 5 example projects, a populated tool breakdown, and an active 5-hour block.

When you're ready to see your own data, run `python3 analyzer.py` — it overwrites `claude-usage-data.json` with the real thing.

### Reproducibility

The demo data is deterministic. The generator (committed below as a comment block) uses `random.seed(42)` so the file is identical every time it's regenerated. If you want to tweak it, copy the block into a `.py` file, change the seed or constants, and re-run.

### Generator

The source generator is `examples/generate_demo_data.py`. Edit the constants at the top (date, projects, tools, model weights) and re-run:

```bash
python3 examples/generate_demo_data.py
```

Standard library only — no dependencies.
