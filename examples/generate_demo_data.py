#!/usr/bin/env python3
"""
Deterministic generator for `examples/demo-data.json`.

The output is shaped exactly like what `analyzer.py` produces, so the
dashboard can be previewed without running against real logs.

Run:
    python3 examples/generate_demo_data.py

Re-runs are stable because of `random.seed(42)`.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

random.seed(42)
NOW = datetime(2026, 5, 15, 14, 30, tzinfo=timezone.utc)  # frozen "now" for the demo

PROJECTS = [
    ("my-blog",          "my-blog"),
    ("ml-experiments",   "ml-experiments"),
    ("side-project",     "side-project"),
    ("client-dashboard", "client-dashboard"),
    ("playground",       "playground"),
    ("(root)",           "(root)"),
]
TOOLS = ["Bash","Edit","Read","Write","TodoWrite","Grep","Glob","WebFetch","Task","NotebookEdit"]
PRICING = {
    "opus":    {"input": 5.00, "output": 25.00},
    "sonnet":  {"input": 3.00, "output": 15.00},
    "haiku":   {"input": 1.00, "output": 5.00},
    "unknown": {"input": 3.00, "output": 15.00},
}


def gen_days():
    by_day = []
    for i in range(70):
        d = NOW - timedelta(days=69 - i)
        is_weekend = d.weekday() >= 5
        active = (not is_weekend and random.random() < 0.85) or (is_weekend and random.random() < 0.35)
        if not active:
            by_day.append({
                "date": d.date().isoformat(), "active_minutes": 0.0,
                "cost": 0.0, "input": 0, "output": 0,
                "cache_read": 0, "cache_write": 0, "messages": 0,
                "effective_tokens": 0, "by_model": {},
            })
            continue
        msgs = random.randint(20, 180)
        if random.random() < 0.12:
            msgs = random.randint(180, 420)
        input_t  = msgs * random.randint(80, 240)
        output_t = msgs * random.randint(180, 520)
        cache_r  = msgs * random.randint(4000, 18000)
        cache_w  = msgs * random.randint(400, 2400)
        roll = random.random()
        model = "sonnet" if roll < 0.6 else ("opus" if roll < 0.9 else "haiku")
        cost = (
            input_t  * PRICING[model]["input"] / 1_000_000
          + output_t * PRICING[model]["output"] / 1_000_000
          + cache_w  * PRICING[model]["input"] * 1.25 / 1_000_000
          + cache_r  * PRICING[model]["input"] * 0.10 / 1_000_000
        )
        eff = input_t + output_t + cache_w
        active_min = round(random.uniform(0.5, 4.5) * (msgs / 60), 1)
        by_day.append({
            "date": d.date().isoformat(),
            "active_minutes": active_min,
            "cost": round(cost, 4),
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
    mb = defaultdict(lambda: {"cost":0,"messages":0,"input":0,"output":0,
                                "cache_read":0,"cache_write":0,"active_minutes":0})
    for d in by_day:
        k = d["date"][:7]
        for f in ("cost","messages","input","output","cache_read","cache_write","active_minutes"):
            mb[k][f] += d[f] if f != "messages" else d["messages"]
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
            "messages_per_active_day": round(v["messages"] / active_days, 1) if active_days else 0,
        })

    # by_model
    bmt = defaultdict(lambda: {"cost":0,"messages":0,"input":0,"output":0,
                                  "cache_read":0,"cache_write":0})
    for d in by_day:
        if d["messages"] == 0: continue
        m = next(iter(d["by_model"]))
        for f in ("cost","input","output","cache_read","cache_write"):
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
            "sessions": random.randint(int(w * 40) + 2, int(w * 80) + 5),
        })

    # by_tool
    by_tool = []
    for i, t in enumerate(TOOLS):
        c = max(8, int(2200 * (0.6 ** i) * random.uniform(0.7, 1.3)))
        by_tool.append({"name": t, "count": c})
    by_tool.sort(key=lambda x: -x["count"])

    # sessions
    sessions = []
    for i in range(10):
        end = NOW - timedelta(days=random.randint(0, 13), hours=random.randint(0, 18))
        start = end - timedelta(minutes=random.randint(5, 120))
        sessions.append({
            "sessionId": f"demo-{i:04d}-{random.randint(1000, 9999):04d}",
            "project": random.choice(PROJECTS)[0],
            "first": start.isoformat(), "last": end.isoformat(),
            "cost": round(random.uniform(0.05, 4.5), 4),
            "messages": random.randint(5, 95),
            "model": random.choices(["sonnet", "opus", "haiku"], weights=[6, 3, 1])[0],
        })
    sessions.sort(key=lambda s: s["last"], reverse=True)

    current_block = {
        "now": NOW.isoformat(),
        "window_hours": 5,
        "started_at": (NOW - timedelta(hours=3, minutes=12)).isoformat(),
        "effective_tokens": 1_847_500,
        "cost": 6.42,
        "messages": 53,
        "tools": [
            {"name": "Bash", "count": 11}, {"name": "Edit", "count": 8},
            {"name": "Read", "count": 7},  {"name": "Write", "count": 3},
            {"name": "Grep", "count": 2},
        ],
    }

    summary = {
        "generated_at": NOW.isoformat(),
        "totals": {
            "input_tokens": total["input"], "output_tokens": total["output"],
            "cache_read": total["cache_read"],
            "cache_write_5m": total["cache_write"], "cache_write_1h": 0,
            "cost": round(total["cost"], 4),
            "cost_input": round(total["input"] * 3 / 1_000_000, 4),
            "cost_output": round(total["output"] * 15 / 1_000_000, 4),
            "cost_cache": round(total["cost"] - (total["input"] * 3 + total["output"] * 15) / 1_000_000, 4),
            "savings_vs_no_cache": round(
                sum(d["cache_read"] * 3 * 0.9 / 1_000_000 for d in by_day), 4
            ),
            "messages": total["msgs"],
        },
        "pricing": PRICING,
        "by_day": by_day, "by_month": by_month, "by_model": by_model,
        "by_project": by_project, "by_tool": by_tool,
        "recent_sessions": sessions, "current_block": current_block,
        "files_scanned": 87,
    }

    out = Path(__file__).resolve().parent / "demo-data.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Wrote {out}")
    print(f"  Days: {len(by_day)} | Total cost: ${total['cost']:.2f} | Messages: {total['msgs']:,}")


if __name__ == "__main__":
    main()
