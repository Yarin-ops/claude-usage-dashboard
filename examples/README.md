# Examples

## `demo-data.json`

A synthetic dataset shaped exactly like what `analyzer.py` produces. Every number is invented, and its `demo` flag makes the dashboard say so. `demo-data.js` is the same data for pages opened from `file://`.

### How to use

Open `index.html?demo`, or click **See it with demo data** on the first-run screen.

You'll see six months of synthetic activity with a mix of Fable / Opus / Sonnet / Haiku, 6 example projects, a populated tool breakdown, and an active 5-hour window.

When you're ready to see your own data, run `python3 analyzer.py` and open `index.html` without `?demo`.

### Reproducibility

The demo data is deterministic. The generator uses `random.seed(42)`, so the file is identical every time it's regenerated.

### Generator

The source generator is `examples/generate_demo_data.py`. Edit the constants at the top (date, projects, tools, model weights) and re-run:

```bash
python3 examples/generate_demo_data.py
```

Standard library only, plus the price table from `analyzer.py`.
