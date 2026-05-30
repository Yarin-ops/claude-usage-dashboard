#!/usr/bin/env python3
"""
Claude Usage Dashboard — analyzer.

Scans ~/.claude/projects/**/*.jsonl (the local logs Claude Code writes), extracts
every assistant message with token usage, computes cost using current Anthropic
public pricing, and emits a compact JSON summary consumed by index.html.

Run once:        python3 analyzer.py
Watch mode:      python3 analyzer.py --watch
                 python3 analyzer.py --watch --interval=15

Output:          claude-usage-data.json (+ .js fallback for file:// loading),
                 written as a sibling of index.html.

No network calls. No API key. Everything runs locally.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOME = Path.home()
# Override with CLAUDE_DIR=/path/to/.claude if your logs live elsewhere.
CLAUDE_PROJECTS = Path(os.environ.get("CLAUDE_DIR") or (HOME / ".claude")) / "projects"
PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_FILE    = PROJECT_ROOT / "claude-usage-data.json"
OUTPUT_FILE_JS = PROJECT_ROOT / "claude-usage-data.js"

# Pricing in USD per 1M tokens (May 2026, Anthropic public pricing).
# Cache write 5m = 1.25x input ; cache write 1h = 2x input ; cache read = 0.10x input.
PRICING = {
    "opus":    {"input": 5.00,  "output": 25.00},
    "sonnet":  {"input": 3.00,  "output": 15.00},
    "haiku":   {"input": 1.00,  "output": 5.00},
    "unknown": {"input": 3.00,  "output": 15.00},
}

CACHE_WRITE_5M_MULT = 1.25
CACHE_WRITE_1H_MULT = 2.00
CACHE_READ_MULT     = 0.10


def classify_model(model_id: str) -> str:
    if not model_id:
        return "unknown"
    m = model_id.lower()
    if "opus" in m:
        return "opus"
    if "sonnet" in m:
        return "sonnet"
    if "haiku" in m:
        return "haiku"
    return "unknown"


def project_label(folder_name: str) -> str:
    """Turn the encoded project folder back into something human-readable.

    Claude Code encodes a project's absolute path as its folder name with
    every `/` replaced by `-`. For example, `/Users/alex/code/my-app` becomes
    `-Users-alex-code-my-app`. We try to reverse that with a best effort, then
    strip everything up to the user's home for brevity.
    """
    if not folder_name.startswith("-"):
        return folder_name
    # Restore the leading slash, then convert structural dashes to slashes.
    # We don't know which dashes are structural vs. literal-in-a-folder-name,
    # so we err on the side of structure and accept occasional rough labels.
    rest = folder_name.lstrip("-")
    rest = re.sub(r"-+$", "", rest)
    rest = rest.replace("-", "/")
    # Trim the user home prefix if it appears.
    try:
        home_no_slash = str(HOME).lstrip("/")
        if rest.startswith(home_no_slash + "/"):
            rest = "~/" + rest[len(home_no_slash) + 1:]
        elif rest == home_no_slash:
            rest = "~"
    except Exception:
        pass
    return rest or "(root)"


def cost_for_entry(model_bucket: str, usage: dict) -> dict:
    price = PRICING.get(model_bucket, PRICING["unknown"])
    in_per_tok  = price["input"]  / 1_000_000
    out_per_tok = price["output"] / 1_000_000

    input_tokens  = usage.get("input_tokens", 0) or 0
    output_tokens = usage.get("output_tokens", 0) or 0
    cache_read    = usage.get("cache_read_input_tokens", 0) or 0
    cache_create  = usage.get("cache_creation_input_tokens", 0) or 0

    cc = usage.get("cache_creation", {}) or {}
    cache_5m = cc.get("ephemeral_5m_input_tokens", 0) or 0
    cache_1h = cc.get("ephemeral_1h_input_tokens", 0) or 0
    # If we have the breakdown, use it; otherwise fall back to total cache_create as 5m.
    if cache_5m == 0 and cache_1h == 0 and cache_create:
        cache_5m = cache_create

    cost_input        = input_tokens * in_per_tok
    cost_output       = output_tokens * out_per_tok
    cost_cache_read   = cache_read * in_per_tok * CACHE_READ_MULT
    cost_cache_5m     = cache_5m  * in_per_tok * CACHE_WRITE_5M_MULT
    cost_cache_1h     = cache_1h  * in_per_tok * CACHE_WRITE_1H_MULT

    # Hypothetical cost if cache reads had been full-priced inputs (= savings).
    savings_vs_no_cache = cache_read * in_per_tok * (1 - CACHE_READ_MULT)

    total = cost_input + cost_output + cost_cache_read + cost_cache_5m + cost_cache_1h

    return {
        "input_tokens":  input_tokens,
        "output_tokens": output_tokens,
        "cache_read":    cache_read,
        "cache_write_5m": cache_5m,
        "cache_write_1h": cache_1h,
        "cost":           total,
        "cost_input":     cost_input,
        "cost_output":    cost_output,
        "cost_cache":     cost_cache_read + cost_cache_5m + cost_cache_1h,
        "savings_vs_no_cache": savings_vs_no_cache,
    }


def iter_assistant_entries(jsonl_path: Path):
    try:
        with jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("type") != "assistant":
                    continue
                msg = rec.get("message") or {}
                usage = msg.get("usage") or {}
                if not usage:
                    continue
                yield rec, msg, usage
    except (OSError, IOError):
        return


def extract_tool_names(msg: dict) -> list[str]:
    """Pulls every tool_use block name out of an assistant message's content."""
    content = msg.get("content")
    if not isinstance(content, list):
        return []
    names = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            name = block.get("name")
            if name:
                names.append(name)
    return names


def main():
    if not CLAUDE_PROJECTS.exists():
        print(f"No Claude data found at {CLAUDE_PROJECTS}", file=sys.stderr)
        sys.exit(1)

    totals = {
        "input_tokens": 0, "output_tokens": 0,
        "cache_read": 0, "cache_write_5m": 0, "cache_write_1h": 0,
        "cost": 0.0, "cost_input": 0.0, "cost_output": 0.0, "cost_cache": 0.0,
        "savings_vs_no_cache": 0.0,
        "messages": 0,
    }
    by_day      = defaultdict(lambda: {"cost": 0.0, "input": 0, "output": 0,
                                        "cache_read": 0, "cache_write": 0, "messages": 0,
                                        "effective_tokens": 0,
                                        "by_model": defaultdict(int)})
    by_month    = defaultdict(lambda: {"cost": 0.0, "messages": 0,
                                        "input": 0, "output": 0,
                                        "cache_read": 0, "cache_write": 0})
    by_model    = defaultdict(lambda: {"cost": 0.0, "messages": 0,
                                        "input": 0, "output": 0,
                                        "cache_read": 0, "cache_write": 0})
    by_project  = defaultdict(lambda: {"cost": 0.0, "messages": 0,
                                        "input": 0, "output": 0,
                                        "cache_read": 0, "cache_write": 0,
                                        "sessions": set(), "label": ""})
    by_session  = {}
    by_tool     = defaultdict(int)  # tool_name -> total invocations
    # Approx active wall-clock time per day, computed by summing gaps
    # < IDLE_GAP_MIN between consecutive timestamps inside the same day.
    by_day_timestamps = defaultdict(list)
    IDLE_GAP_MIN = 5  # minutes
    seen_msgs = set()

    # 5-hour rolling block: Claude Code rate-limits on a 5h window. We track
    # effective tokens (input + output + cache_write — NOT cache_read) for
    # every message in the last 5 hours, plus the window's start (oldest msg).
    now_utc = datetime.now(timezone.utc)
    block_cutoff = now_utc - timedelta(hours=5)
    block_effective_tokens = 0
    block_cost = 0.0
    block_messages = 0
    block_start = None  # earliest timestamp seen inside the window
    block_by_tool = defaultdict(int)

    jsonl_files = sorted(CLAUDE_PROJECTS.rglob("*.jsonl"))

    for jsonl in jsonl_files:
        try:
            folder = jsonl.parent.name
        except Exception:
            folder = "unknown"
        plabel = project_label(folder)

        for rec, msg, usage in iter_assistant_entries(jsonl):
            # De-duplicate via message id across files (resumed sessions etc).
            mid = msg.get("id")
            if mid and mid in seen_msgs:
                continue
            if mid:
                seen_msgs.add(mid)

            model_id = msg.get("model") or "unknown"
            bucket = classify_model(model_id)
            costs = cost_for_entry(bucket, usage)

            ts_raw = rec.get("timestamp")
            if not ts_raw:
                continue
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            except Exception:
                continue
            day_key   = ts.date().isoformat()
            month_key = f"{ts.year:04d}-{ts.month:02d}"
            by_day_timestamps[day_key].append(ts)

            # --- totals ---
            for k in ("input_tokens", "output_tokens", "cache_read",
                      "cache_write_5m", "cache_write_1h",
                      "cost", "cost_input", "cost_output", "cost_cache",
                      "savings_vs_no_cache"):
                totals[k] += costs[k]
            totals["messages"] += 1

            cache_write = costs["cache_write_5m"] + costs["cache_write_1h"]

            # --- by day ---
            effective = costs["input_tokens"] + costs["output_tokens"] + cache_write
            d = by_day[day_key]
            d["cost"]       += costs["cost"]
            d["input"]      += costs["input_tokens"]
            d["output"]     += costs["output_tokens"]
            d["cache_read"] += costs["cache_read"]
            d["cache_write"]+= cache_write
            d["effective_tokens"] += effective
            d["by_model"][bucket] += effective
            d["messages"]   += 1

            # --- by month ---
            m = by_month[month_key]
            m["cost"]       += costs["cost"]
            m["input"]      += costs["input_tokens"]
            m["output"]     += costs["output_tokens"]
            m["cache_read"] += costs["cache_read"]
            m["cache_write"]+= cache_write
            m["messages"]   += 1

            # --- by model ---
            mm = by_model[bucket]
            mm["cost"]       += costs["cost"]
            mm["input"]      += costs["input_tokens"]
            mm["output"]     += costs["output_tokens"]
            mm["cache_read"] += costs["cache_read"]
            mm["cache_write"]+= cache_write
            mm["messages"]   += 1

            # --- by project ---
            pp = by_project[folder]
            pp["label"]      = plabel
            pp["cost"]       += costs["cost"]
            pp["input"]      += costs["input_tokens"]
            pp["output"]     += costs["output_tokens"]
            pp["cache_read"] += costs["cache_read"]
            pp["cache_write"]+= cache_write
            pp["messages"]   += 1
            sid = rec.get("sessionId")
            if sid:
                pp["sessions"].add(sid)

            # --- by session ---
            if sid:
                s = by_session.get(sid)
                if not s:
                    s = {"sessionId": sid, "project": plabel,
                          "first": ts_raw, "last": ts_raw, "cost": 0.0,
                          "messages": 0, "model": bucket}
                    by_session[sid] = s
                s["cost"]     += costs["cost"]
                s["messages"] += 1
                if ts_raw < s["first"]:
                    s["first"] = ts_raw
                if ts_raw > s["last"]:
                    s["last"]  = ts_raw
                # Track latest model used.
                s["model"] = bucket

            # --- by tool ---
            tool_names = extract_tool_names(msg)
            for tname in tool_names:
                by_tool[tname] += 1

            # --- current 5-hour block ---
            if ts >= block_cutoff:
                # Effective tokens = what counts toward rate limits.
                # Cache reads are deliberately excluded.
                effective = (costs["input_tokens"] + costs["output_tokens"]
                              + cache_write)
                block_effective_tokens += effective
                block_cost += costs["cost"]
                block_messages += 1
                if block_start is None or ts < block_start:
                    block_start = ts
                for tname in tool_names:
                    block_by_tool[tname] += 1

    # Convert sets to counts for projects.
    projects_out = []
    for folder, pp in by_project.items():
        projects_out.append({
            "folder":      folder,
            "label":       pp["label"],
            "cost":        round(pp["cost"], 4),
            "messages":    pp["messages"],
            "input":       pp["input"],
            "output":      pp["output"],
            "cache_read":  pp["cache_read"],
            "cache_write": pp["cache_write"],
            "sessions":    len(pp["sessions"]),
        })
    projects_out.sort(key=lambda x: x["cost"], reverse=True)

    # Compute active minutes per day from message timestamps.
    active_minutes_by_day = {}
    for k, stamps in by_day_timestamps.items():
        stamps.sort()
        total_sec = 0.0
        for i in range(1, len(stamps)):
            gap = (stamps[i] - stamps[i-1]).total_seconds()
            if gap <= IDLE_GAP_MIN * 60:
                total_sec += gap
        # Treat every message as worth IDLE_GAP_MIN/2 of context on its own
        # (otherwise a one-shot question registers as 0 minutes).
        total_sec += len(stamps) * (IDLE_GAP_MIN * 60 / 2) * 0.0  # disabled to stay literal
        active_minutes_by_day[k] = round(total_sec / 60.0, 1)

    days_out = []
    for k in sorted(by_day.keys()):
        v = by_day[k]
        # Flatten defaultdict for JSON and skip the nested by_model field
        # while we copy scalars, then attach by_model as a plain dict.
        day_obj = {"date": k, "active_minutes": active_minutes_by_day.get(k, 0)}
        for kk, vv in v.items():
            if kk == "by_model":
                day_obj["by_model"] = dict(vv)
            else:
                day_obj[kk] = round(vv, 4) if isinstance(vv, float) else vv
        days_out.append(day_obj)

    months_out = []
    for k in sorted(by_month.keys()):
        v = by_month[k]
        months_out.append({"month": k, **{kk: (round(vv, 4) if isinstance(vv, float) else vv)
                                          for kk, vv in v.items()}})

    models_out = []
    for k, v in by_model.items():
        models_out.append({"model": k, **{kk: (round(vv, 4) if isinstance(vv, float) else vv)
                                          for kk, vv in v.items()}})
    models_out.sort(key=lambda x: x["cost"], reverse=True)

    sessions_out = sorted(by_session.values(), key=lambda s: s["last"], reverse=True)[:40]
    for s in sessions_out:
        s["cost"] = round(s["cost"], 4)

    # Per-month rollup: active days, hours, top projects, top models.
    month_details = {}
    for m_iso in by_month.keys():
        month_days = [d for d in days_out if d["date"].startswith(m_iso)]
        active_days = sum(1 for d in month_days if d["messages"] > 0)
        active_minutes = sum(d.get("active_minutes", 0) for d in month_days)

        # Aggregate this month's projects & models by re-scanning by_session/by_day is heavy.
        # Easier: track during the main loop. We'll do a second pass here using the
        # already-collected per-day info to keep it simple — projects/models per month
        # are computed below using a fresh scan over by_session+filter.
        month_details[m_iso] = {
            "active_days": active_days,
            "active_minutes": round(active_minutes, 1),
            "active_hours": round(active_minutes / 60.0, 1),
            "messages_per_active_day": round(
                sum(d["messages"] for d in month_days) / active_days, 1
            ) if active_days else 0,
        }
    # Attach to months_out.
    for m in months_out:
        m.update(month_details.get(m["month"], {}))

    # --- 5h block window summary ---
    # 7d global tool ranking, plus the in-window ranking.
    tools_out = sorted(
        ({"name": k, "count": v} for k, v in by_tool.items()),
        key=lambda x: x["count"], reverse=True
    )
    block_tools_out = sorted(
        ({"name": k, "count": v} for k, v in block_by_tool.items()),
        key=lambda x: x["count"], reverse=True
    )
    block_summary = {
        "now":                 now_utc.isoformat(),
        "window_hours":        5,
        "started_at":          block_start.isoformat() if block_start else None,
        "effective_tokens":    block_effective_tokens,
        "cost":                round(block_cost, 4),
        "messages":            block_messages,
        "tools":               block_tools_out[:8],
    }

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "totals": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in totals.items()},
        "pricing": PRICING,
        "by_day":     days_out,
        "by_month":   months_out,
        "by_model":   models_out,
        "by_project": projects_out,
        "by_tool":    tools_out,
        "recent_sessions": sessions_out,
        "current_block":   block_summary,
        "files_scanned": len(jsonl_files),
    }

    payload = json.dumps(summary, ensure_ascii=False, indent=2)
    OUTPUT_FILE.write_text(payload)
    # Also write a JS version so the dashboard works opened directly from
    # the filesystem (file:// blocks fetch() of sibling JSON in most browsers).
    OUTPUT_FILE_JS.write_text("window.CLAUDE_USAGE_DATA = " + payload + ";\n")
    print(f"Wrote {OUTPUT_FILE}")
    print(f"Wrote {OUTPUT_FILE_JS}")
    print(f"  Files scanned:   {len(jsonl_files)}")
    print(f"  Messages:        {totals['messages']:,}")
    print(f"  Total cost:      ${totals['cost']:.2f}")
    print(f"  Cache savings:   ${totals['savings_vs_no_cache']:.2f}")


if __name__ == "__main__":
    if "--watch" in sys.argv:
        # Re-run every N seconds (default 30) so the dashboard stays live.
        interval = 30
        for arg in sys.argv:
            if arg.startswith("--interval="):
                try:
                    interval = max(5, int(arg.split("=", 1)[1]))
                except ValueError:
                    pass
        print(f"Watching ~/.claude/projects — re-running every {interval}s. Ctrl+C to stop.")
        while True:
            try:
                main()
            except Exception as e:
                print(f"  (run failed: {e}; retrying next tick)", file=sys.stderr)
            time.sleep(interval)
    else:
        main()
