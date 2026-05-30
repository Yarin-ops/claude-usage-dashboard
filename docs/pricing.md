# Pricing & cost calculation

This document explains exactly how the dashboard turns raw token counts into a dollar number, and what the "cache savings" line really means. If you ever need to update prices or audit the math, this is the reference.

## Pricing table

All prices are USD per **1 million tokens**, current as of May 2026 (Anthropic public pricing). They live at the top of `analyzer.py` in the `PRICING` dict — update them there when Anthropic publishes new numbers.

| Model bucket | Input | Output |
|---|---:|---:|
| Opus    | $5.00  | $25.00 |
| Sonnet  | $3.00  | $15.00 |
| Haiku   | $1.00  | $5.00  |
| Unknown | $3.00  | $15.00 (= Sonnet default) |

Model "bucket" is derived from the model id in each log entry: any id containing `opus` → Opus, `sonnet` → Sonnet, `haiku` → Haiku, anything else → Unknown.

## Cache pricing

Anthropic charges three different rates on cached tokens. They're multipliers on the **input** price for the matching model bucket:

| Operation | Multiplier on input price |
|---|---:|
| Cache write — 5-minute TTL  | 1.25× |
| Cache write — 1-hour TTL    | 2.00× |
| Cache read                  | 0.10× |

So a Sonnet input token costs $3.00 / M as a fresh read, $3.75 / M when written into the 5-min cache, $6.00 / M when written into the 1-hour cache, and **$0.30 / M when read back from cache**. Cache reads are why Claude Code is cheap to actually use — the bulk of your tokens land in the read column.

## How the cost of one message is computed

For each assistant message in the logs:

```
cost_input        = input_tokens          × input_price
cost_output       = output_tokens         × output_price
cost_cache_read   = cache_read_tokens     × input_price × 0.10
cost_cache_5m     = cache_write_5m_tokens × input_price × 1.25
cost_cache_1h     = cache_write_1h_tokens × input_price × 2.00

total = cost_input + cost_output + cost_cache_read + cost_cache_5m + cost_cache_1h
```

Cache write tokens come from two fields in the usage payload: `cache_creation.ephemeral_5m_input_tokens` and `cache_creation.ephemeral_1h_input_tokens`. If only the older flat `cache_creation_input_tokens` is present, the analyzer treats it all as 5-minute writes — slightly conservative.

## Cache savings line

The headline number "saved in cache" in the dashboard is calculated as:

```
savings_vs_no_cache = cache_read_tokens × input_price × (1 - 0.10)
```

In plain English: this is what the cached input *would have cost* if Anthropic had no cache and every read was full-priced. It is **not money you put back in your pocket** — you never had a choice to pay the higher number. It's a useful sanity-check on how aggressive the cache is, nothing more.

That's why the dashboard's headline framing is **Pay vs Use** rather than "savings". The reality-check banner makes this explicit: the only real cash out is your subscription + any direct API spend you've entered.

## Effective tokens (used by the 5-hour block and the heatmap)

"Effective tokens" is a derived metric the dashboard uses where the relevant question is *what counts toward rate limits*, not *what costs money*. It is:

```
effective = input + output + cache_write_5m + cache_write_1h
```

Cache reads are excluded. They're cheap and they don't count toward Anthropic's 5-hour window limit, so a dashboard that included them in the ring would be misleading.

## Token accounting differences vs. similar tools

If you're comparing this dashboard's numbers against another (Anthropic's console, a third-party viewer, `iftahs/claude-dashboard`), expect small drift from:

- **Deduplication** — the analyzer dedupes by `message.id` across `.jsonl` files. Resumed sessions write the same message in multiple files; uniqueness is per-id.
- **Cache 5m vs 1h split** — older log entries don't break out the two TTLs, so the analyzer defaults to 5m which is slightly cheaper.
- **Pricing date** — Anthropic updates pricing; if your tool is on an older snapshot, totals will diverge.
- **Model classification** — model ids that don't include `opus/sonnet/haiku` fall into "Unknown" and get priced like Sonnet.

None of these matter for usage patterns — they affect total dollars by at most a few percent.
