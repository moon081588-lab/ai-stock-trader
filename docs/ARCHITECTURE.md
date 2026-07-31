# Architecture

## Layers

```
HTTP  ──▶  app/api/routes.py      thin; validation + error mapping only
           app/api/deps.py        singletons, price fanout
           │
Logic ──▶  app/services/*         forecasting, portfolio, dividends, news, paper trading
           app/core/analytics.py  shared risk math
           │
Data  ──▶  app/data/providers.py  MarketDataProvider ABC
           app/services/news.py   NewsProvider + SentimentScorer ABCs
           │
State ──▶  data/store/portfolio.json
```

Rule: routes never do math, services never do HTTP. That separation is what makes
the services unit-testable without network access — see `tests/test_core.py`.

## Key decisions

**Lot-level holdings.** A position is derived, not stored. Average cost, FIFO
sells, holding-period classification, and "did I own this on the ex-date?" all
need the individual purchase records. Collapsing to `{symbol: qty, avg_cost}`
early would make those unrecoverable.

**Provider interfaces.** yfinance is unofficial and rate-limited — fine for
research, wrong for anything load-bearing. `MarketDataProvider` exists so
replacing it is a one-class change with no service edits.

**Forecast honesty.** Every projection returns a 5th–95th percentile band and a
confidence that decays with horizon. A point estimate for a 12-month stock price
without an interval would be misleading, so the schema does not allow one.

**Deterministic Monte Carlo.** The simulator is seeded. Reproducible output
matters more than fresh randomness when you are comparing model versions.

**No broker client.** Not an omission. The codebase has no order-routing path,
and adding one should be a deliberate, separately reviewed decision.

## Persistence

JSON file, written under a lock, loaded on startup. Adequate for single-user
local use. The `PortfolioStore` interface is the swap point for SQLite/Postgres
when transaction history and multi-user support arrive.

## Where the AI goes

Two seams are already carved out:

1. `SentimentScorer` — replace the lexicon with an LLM call that reads full
   articles rather than headlines.
2. A future `services/signals.py` — combine forecast output, sentiment, and
   fundamentals into a ranked view, with the reasoning surfaced rather than
   hidden behind a score.

Both are additive. Neither requires changing existing services.
