# AI Stock Trader

Equity research toolkit: price projections from historical data, portfolio and
dividend analytics, news sentiment signals, and a paper-trading simulator.

> **Research tool, not advice.** Every number here is a statistical projection
> from historical data. The app never connects to a broker and never places a
> real order. Nothing in it is investment advice.

## Quick start

```bash
cd ai-stock-trader
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # no keys required to start

uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for the interactive API.

```bash
pytest        # run the test suite
ruff check .  # lint
```

## What works today

| Area | Endpoint | Notes |
|---|---|---|
| Quotes | `GET /api/v1/market/quote/{symbol}` | yfinance, no API key |
| Price history | `GET /api/v1/market/history/{symbol}` | OHLCV, adjusted |
| Projections | `GET /api/v1/forecast/{symbol}` | `drift`, `monte_carlo`, `linear_trend` |
| Portfolio | `GET /api/v1/portfolio` | Positions, cost basis, unrealized P/L, weights |
| Add holding | `POST /api/v1/portfolio/lots` | Lot-level, so cost basis stays accurate |
| Dividends | `GET /api/v1/portfolio/dividends` | TTM income, forward projection, yield, yield-on-cost |
| News | `GET /api/v1/news/{symbol}` | Headlines + lexicon sentiment |
| Paper trade | `POST /api/v1/paper/orders` | Simulated fill with slippage |

## Layout

```
app/
  main.py          FastAPI entrypoint
  config.py        Settings from .env
  api/             Routes + dependency wiring (thin)
  core/analytics.py  Sharpe, max drawdown, beta, VaR, CAGR
  data/providers.py  Market data behind one swappable interface
  models/schemas.py  Pydantic contracts
  services/        Forecasting, portfolio, dividends, news, paper trading
tests/             Pure-logic tests, no network
docs/              Architecture + roadmap
```

## Design notes

- **Providers are pluggable.** `MarketDataProvider` and `NewsProvider` are ABCs.
  yfinance is the zero-key default; Polygon or Alpha Vantage drop in without
  touching services.
- **Baselines before ML.** Drift and Monte Carlo ship first so any future model
  has a benchmark it must beat.
- **Lots, not positions.** Holdings are stored as individual purchase lots, which
  is what correct cost basis, FIFO sells, and dividend accrual require.
- **No execution path.** There is no broker client in the codebase by design.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/ROADMAP.md](docs/ROADMAP.md).
