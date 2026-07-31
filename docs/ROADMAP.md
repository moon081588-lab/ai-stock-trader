# Roadmap

Phase 1 is built. Everything below it is planned.

## Phase 1 — Foundation ✅

- [x] FastAPI skeleton, settings, logging
- [x] Market data behind a swappable provider interface
- [x] Baseline forecasts: drift, Monte Carlo, linear trend, with uncertainty bands
- [x] Lot-level portfolio, cost basis, unrealized P/L, weights
- [x] Dividend analytics: TTM income, forward projection, yield, yield-on-cost
- [x] News headlines + lexicon sentiment
- [x] Paper trading with slippage and FIFO sells
- [x] Risk metrics: Sharpe, max drawdown, beta, VaR, CAGR
- [x] Test suite covering the pure-logic layer

## Phase 2 — Better data

- [ ] Disk cache with TTL so yfinance isn't hit on every request
- [ ] SQLite store: transaction history, realized gains, time-weighted return
- [ ] Fundamentals: P/E, margins, revenue growth, debt
- [ ] Dividend calendar for genuine upcoming-payment forecasts
- [ ] Corporate actions: splits and spinoffs, which silently corrupt cost basis

## Phase 3 — Real forecasting

- [ ] Backtesting harness — walk-forward, no lookahead
- [ ] Feature pipeline: momentum, volatility regime, volume, sector relatives
- [ ] Gradient-boosted return model, scored against the drift baseline
- [ ] Ensemble across methods with per-regime weighting
- [ ] Honest accuracy tracking: publish where the model is wrong, not just hit rate

## Phase 4 — AI layer

- [ ] LLM sentiment over full article text, not headlines
- [ ] Earnings-call transcript summarization
- [ ] `services/signals.py` — combine forecast + sentiment + fundamentals into a
      ranked view with written reasoning
- [ ] Natural-language portfolio Q&A ("what's my tech concentration risk?")

## Phase 5 — Interface

- [ ] React dashboard: holdings, allocation, dividend calendar, forecast charts
- [ ] Watchlists and alerts
- [ ] Scheduled daily digest

## Phase 6 — Portfolio engineering

- [ ] Correlation matrix and concentration warnings
- [ ] Efficient-frontier optimizer
- [ ] Rebalancing suggestions with tax-lot awareness
- [ ] Monte Carlo retirement/withdrawal modeling

## Explicitly out of scope

Live order execution. The app models and simulates; a human places every real
trade. If broker integration is ever added, it belongs behind an explicit,
separately reviewed boundary — not folded into the analytics path.
