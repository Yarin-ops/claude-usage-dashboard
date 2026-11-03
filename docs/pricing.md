# Pricing & cost calculation

This document explains exactly how the dashboard turns raw token counts into a dollar number, and what the "cache savings" line really means. If you ever need to update prices or audit the math, this is the reference.

## Pricing table

All prices are USD per **1 million tokens**, from [Anthropic's public price list](https://platform.claude.com/docs/en/about-claude/pricing), checked November 3, 2026. They live at the top of `analyzer.py` in the `PRICING` dict, keyed by exact model id. Update them there when Anthropic publishes new numbers.

| Model | Input | Output | Cache read |
|---|---:|---:|---:|
| Fable 5.1, Mythos 5.1 | $10.00 | $50.00 | $0.25 |
| Fable 5, Mythos 5 | $10.00 | $50.00 | $1.00 |
| Opus 5.5 | $4.00 | $20.00 | $0.20 |
| Opus 5, 4.8, 4.7, 4.6, 4.5 | $5.00 | $25.00 | $0.50 |
| Opus 4.1, 4 | $15.00 | $75.00 | $1.50 |
| Sonnet 5.5 | $2.00 | $10.00 | $0.10 |
| Sonnet 5 | $2.00 | $10.00 | $0.20 |
| Sonnet 4.6, 4.5, 4 | $3.00 | $15.00 | $0.30 |
| Haiku 5.5 (prompt up to 100K tokens) | $0.10 | $0.50 | $0.01 |
| Haiku 5.5 (prompt over 100K tokens) | $0.50 | $2.50 | $0.05 |
| Haiku 4.5 | $1.00 | $5.00 | $0.10 |
| Haiku 3.5 | $0.80 | $4.00 | $0.08 |

The most specific id wins, so `claude-opus-5-5` never reads as `claude-opus-5`. An id the table doesn't list is priced at its family's current rates, and anything outside the four families is priced like the current Sonnet and shown as Unknown.

Not modeled: fast mode, Batch API discounts, and data residency premiums. The logs are treated as standard-rate traffic.

## Cache pricing

Cache writes are multipliers on the model's **input** price. Cache reads have their own listed price, because the ratio to input is no longer a flat 0.10×.

| Operation | Price |
|---|---:|
| Cache write, 5-minute TTL | 1.25× input |
| Cache write, 1-hour TTL | 2.00× input |
| Cache read | listed per model, see the table above |

So an Opus 5.5 input token costs $4.00 / M as a fresh read, $5.00 / M when written into the 5-minute cache, $8.00 / M when written into the 1-hour cache, and **$0.20 / M when read back from cache**. Cache reads are why Claude Code is cheap to actually use: the bulk of your tokens land in the read column.

## How the cost of one message is computed

For each assistant message in the logs:

```
cost_input        = input_tokens          × input_price
cost_output       = output_tokens         × output_price
cost_cache_read   = cache_read_tokens     × cache_read_price
cost_cache_5m     = cache_write_5m_tokens × input_price × 1.25
cost_cache_1h     = cache_write_1h_tokens × input_price × 2.00

total = cost_input + cost_output + cost_cache_read + cost_cache_5m + cost_cache_1h
```

Cache write tokens come from two fields in the usage payload: `cache_creation.ephemeral_5m_input_tokens` and `cache_creation.ephemeral_1h_input_tokens`. If only the older flat `cache_creation_input_tokens` is present, the analyzer treats it all as 5-minute writes — slightly conservative.

## Cache savings line

The "saved by prompt cache" number in the dashboard is calculated as:

```
savings_vs_no_cache = cache_read_tokens × (input_price - cache_read_price)
```

In plain English: this is what the cached input *would have cost* if Anthropic had no cache and every read was full-priced. It is **not money you put back in your pocket** — you never had a choice to pay the higher number. It's a useful sanity-check on how aggressive the cache is, nothing more.

That's why the dashboard's headline framing is **Pay vs Use** rather than "savings". The note under the headline makes this explicit: the only real cash out is your subscription + any direct API spend you've entered.

## Effective tokens (used by the 5-hour block and the heatmap)

"Effective tokens" is a derived metric the dashboard uses where the relevant question is *what counts toward rate limits*, not *what costs money*. It is:

```
effective = input + output + cache_write_5m + cache_write_1h
```

Cache reads are excluded. They're cheap and they don't count toward Anthropic's 5-hour window limit, so a dashboard that included them in the ring would be misleading.

## Token accounting differences vs. similar tools

If you're comparing this dashboard's numbers against another (Anthropic's console, a third-party viewer, `iftahs/claude-dashboard`), expect small drift from:

- **Deduplication** — the analyzer merges log lines by `message.id` across `.jsonl` files. Claude Code writes one line per content block, and resumed sessions repeat messages in other files. A tool that sums every line can report about twice the tokens.
- **Cache 5m vs 1h split** — older log entries don't break out the two TTLs, so the analyzer defaults to 5m which is slightly cheaper.
- **Pricing date** — Anthropic updates pricing; if your tool is on an older snapshot, totals will diverge.
- **Model classification** — model ids outside the Fable, Opus, Sonnet and Haiku families fall into "Unknown" and get priced like the current Sonnet.

Treat the dollar figures as an estimate. They are good for seeing patterns, not for reconciling a bill.
