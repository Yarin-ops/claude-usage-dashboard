#!/usr/bin/env python3
"""
Deterministic generator for `examples/demo-data.json` and `examples/demo-data.js`.

The output is shaped exactly like what `analyzer.py` produces, so the
dashboard can be previewed without running against real logs. Every number
in it is invented, and the `demo` flag makes the dashboard say so.

Run:
    python3 examples/generate_demo_data.py

Re-runs are stable because of `random.seed(42)`.
"""

from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analyzer import PRICING  # noqa: E402

random.seed(42)
NOW = datetime(2026, 10, 28, 16, 40, tzinfo=timezone.utc)  # frozen "now" for the demo
DAYS = 182  # fills the 26-week heatmap

PROJECTS = [
    ("my-blog",          "my-blog"),
    ("ml-experiments",   "ml-experiments"),
    ("side-project",     "side-project"),
    ("client-dashboard", "client-dashboard"),
    ("playground",       "playground"),
    ("infra-scripts",    "infra-scripts"),
]
TOOLS = ["Bash", "Read", "Edit", "Grep", "Write", "Glob", "TodoWrite", "WebFetch", "Task", "WebSearch"]
MODELS = {
    "opus":   ("claude-opus-5-5", 62),
    "sonnet": ("claude-sonnet-5-5", 24),
    "fable":  ("claude-fable-5-1", 8),
    "haiku":  ("claude-haiku-5-5", 6),
}


def cost_of(model, input_t, output_t, cache_r, cache_w):
    p = PRICING[MODELS[model][0]]
    return (input_t * p["input"] + output_t * p["output"]
            + cache_r * p["cache_read"] + cache_w * p["cache_write_5m"]) / 1_000_000


def gen_days():
    by_day = []
    for i in range(DAYS):
        d = NOW - timedelta(days=DAYS - 1 - i)
        is_weekend = d.weekday() >= 5
        # Usage ramps up over the six months, like someone adopting a new tool.
        ramp = 0.45 + 0.55 * (i / DAYS)
        active = random.random() < (0.3 if is_weekend else 0.86)
        if not active:
            by_day.append({
                "date": d.date().isoformat(), "active_minutes": 0.0,
                "cost": 0.0, "input": 0, "output": 0,
                "cache_read": 0, "cache_write": 0, "messages": 0,
                "effective_tokens": 0, "by_model": {},
            })
            continue
        msgs = int(random.randint(50, 260) * ramp)
        if random.random() < 0.12:
            msgs = int(random.randint(300, 520) * ramp)
        msgs = max(12, msgs)
        input_t  = msgs * random.randint(4, 30)
        output_t = msgs * random.randint(280, 820)
        cache_r  = msgs * random.randint(120_000, 320_000)
        cache_w  = msgs * random.randint(3_000, 12_000)
        model = random.choices(list(MODELS), weights=[w for _, w in MODELS.values()])[0]
        eff = input_t + output_t + cache_w
        by_day.append({
            "date": d.date().isoformat(),
            "active_minutes": round(min(msgs * random.uniform(0.9, 1.5), 560), 1),
            "cost": round(cost_of(model, input_t, output_t, cache_r, cache_w), 4),
            "input": input_t, "output": output_t,
            "cache_read": cache_r, "cache_write": cache_w,
            "messages": msgs,
            "effective_tokens": eff,
            "by_model": {model: eff},
        })
    return by_day


def main():
    by_day = gen_days()
    total = {
        "input": sum(d["input"] for d in by_day),
        "output": sum(d["output"] for d in by_day),
        "cache_read": sum(d["cache_read"] for d in by_day),
        "cache_write": sum(d["cache_write"] for d in by_day),
        "msgs": sum(d["messages"] for d in by_day),
        "cost": sum(d["cost"] for d in by_day),
    }

    # by_month
    mb = defaultdict(lambda: {"cost": 0, "messages": 0, "input": 0, "output": 0,
                              "cache_read": 0, "cache_write": 0, "active_minutes": 0})
    for d in by_day:
        k = d["date"][:7]
        for f in ("cost", "messages", "input", "output", "cache_read", "cache_write", "active_minutes"):
            mb[k][f] += d[f]
    by_month = []
    for k in sorted(mb):
        days_in = [d for d in by_day if d["date"].startswith(k)]
        active_days = sum(1 for d in days_in if d["messages"] > 0)
        v = mb[k]
        by_month.append({
            "month": k,
            "cost": round(v["cost"], 4), "messages": v["messages"],
            "input": v["input"], "output": v["output"],
            "cache_read": v["cache_read"], "cache_write": v["cache_write"],
            "active_days": active_days,
            "active_minutes": round(v["active_minutes"], 1),
            "active_hours": round(v["active_minutes"] / 60, 1),
            "active_projects": random.randint(4, len(PROJECTS)),
            "messages_per_active_day": round(v["messages"] / active_days, 1) if active_days else 0,
        })

    # by_model
    bmt = defaultdict(lambda: {"cost": 0, "messages": 0, "input": 0, "output": 0,
                               "cache_read": 0, "cache_write": 0})
    for d in by_day:
        if d["messages"] == 0:
            continue
        m = next(iter(d["by_model"]))
        for f in ("cost", "input", "output", "cache_read", "cache_write"):
            bmt[m][f] += d[f]
        bmt[m]["messages"] += d["messages"]
    by_model = sorted(
        ({"model": k, **{kk: round(vv, 4) if isinstance(vv, float) else vv for kk, vv in v.items()}}
         for k, v in bmt.items()),
        key=lambda x: x["cost"], reverse=True
    )

    # by_project
    weights = [0.34, 0.22, 0.18, 0.14, 0.08, 0.04]
    by_project = []
    for (label, folder), w in zip(PROJECTS, weights):
        by_project.append({
            "folder": folder, "label": label,
            "cost": round(total["cost"] * w, 4),
            "messages": int(total["msgs"] * w),
            "input": int(total["input"] * w),
            "output": int(total["output"] * w),
            "cache_read": int(total["cache_read"] * w),
            "cache_write": int(total["cache_write"] * w),
            "sessions": random.randint(int(w * 200) + 4, int(w * 400) + 8),
        })

    # by_tool
    by_tool = []
    for i, t in enumerate(TOOLS):
        c = max(40, int(total["msgs"] * 0.42 * (0.62 ** i) * random.uniform(0.85, 1.15)))
        by_tool.append({"name": t, "count": c})
    by_tool.sort(key=lambda x: -x["count"])

    # sessions
    sessions = []
    for i in range(10):
        end = NOW - timedelta(hours=random.randint(i * 5, i * 11 + 4))
        start = end - timedelta(minutes=random.randint(5, 180))
        sessions.append({
            "sessionId": f"demo-{i:04d}-{random.randint(1000, 9999):04d}",
            "project": random.choice(PROJECTS)[0],
            "first": start.isoformat(), "last": end.isoformat(),
            "cost": round(random.uniform(0.4, 14), 4),
            "messages": random.randint(12, 240),
            "model": random.choices(list(MODELS), weights=[w for _, w in MODELS.values()])[0],
        })
    sessions.sort(key=lambda s: s["last"], reverse=True)

    # The current window, priced like everything else.
    block_output, block_write, block_read = 212_400, 2_180_000, 44_600_000
    current_block = {
        "now": NOW.isoformat(),
        "window_hours": 5,
        "started_at": (NOW - timedelta(hours=3, minutes=12)).isoformat(),
        "effective_tokens": block_output + block_write + 2_100,
        "cost": round(cost_of("opus", 2_100, block_output, block_read, block_write), 4),
        "messages": 148,
        "tools": [
            {"name": "Bash", "count": 46}, {"name": "Read", "count": 31},
            {"name": "Edit", "count": 24}, {"name": "Grep", "count": 12},
            {"name": "Write", "count": 5},
        ],
    }

    input_cost = sum(cost_of(m, bmt[m]["input"], 0, 0, 0) for m in bmt)
    output_cost = sum(cost_of(m, 0, bmt[m]["output"], 0, 0) for m in bmt)
    savings = sum(
        bmt[m]["cache_read"] * (PRICING[MODELS[m][0]]["input"] - PRICING[MODELS[m][0]]["cache_read"]) / 1_000_000
        for m in bmt
    )

    summary = {
        "demo": True,
        "generated_at": NOW.isoformat(),
        "totals": {
            "input_tokens": total["input"], "output_tokens": total["output"],
            "cache_read": total["cache_read"],
            "cache_write_5m": total["cache_write"], "cache_write_1h": 0,
            "cost": round(total["cost"], 4),
            "cost_input": round(input_cost, 4),
            "cost_output": round(output_cost, 4),
            "cost_cache": round(total["cost"] - input_cost - output_cost, 4),
            "savings_vs_no_cache": round(savings, 4),
            "messages": total["msgs"],
        },
        "pricing": PRICING,
        "by_day": by_day, "by_month": by_month, "by_model": by_model,
        "by_project": by_project, "by_tool": by_tool,
        "recent_sessions": sessions, "current_block": current_block,
        "files_scanned": 412,
    }

    here = Path(__file__).resolve().parent
    payload = json.dumps(summary, ensure_ascii=False, indent=2)
    (here / "demo-data.json").write_text(payload, encoding="utf-8")
    (here / "demo-data.js").write_text("window.CLAUDE_USAGE_DATA = " + payload + ";\n", encoding="utf-8")
    print(f"Wrote {here / 'demo-data.json'} and demo-data.js")
    print(f"  Days: {len(by_day)} | Total cost: ${total['cost']:.2f} | Messages: {total['msgs']:,}")
    print("  Last month:", by_month[-1]["month"], by_month[-1]["active_hours"], "h", round(by_month[-1]["cost"]), "$")


if __name__ == "__main__":
    main()
