# AI Stock Trader

Equity research toolkit: price projections from historical data, portfolio and
dividend analytics, news sentiment signals, and a paper-trading simulator.

> **Research tool, not advice.** Every number here is a statistical projection
> from historical data. The app never connects to a broker and never places a
> real order. Nothing in it is investment advice.

## Quick start

Two processes. Backend first:

```bash
cd ai-stock-trader
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # no keys required to start

uvicorn app.main:app --reload   # http://127.0.0.1:8000/docs
```

Then the dashboard, in a second terminal:

```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

Vite proxies `/api` to the backend, so there's no CORS setup in dev.

```bash
pytest && ruff check .          # backend
cd frontend && npm run build    # frontend typecheck + bundle
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
| Market board | `GET /api/v1/market/board` | Index cards + ranked movers in one call |
| Watchlist | `GET/POST/DELETE /api/v1/watchlist` | Powers the right rail |
| Stock detail | `GET /api/v1/stocks/{symbol}` | Quote + bars + forecast + risk metrics |

## Screens

- **홈** — index cards with intraday sparklines, filter chips (전체/국내/해외 ×
  거래대금/거래량/시가총액/급상승/급하락), ranked movers table, watchlist rail,
  bottom ticker bar.
- **종목 상세** — candlestick chart with the forecast cone drawn as a continuation
  of history, hover crosshair, range/horizon/method selectors, risk metrics,
  per-horizon projection table, news feed with sentiment.
- **내 계좌** — total value header, holdings table with per-position P/L,
  allocation donut, dividend panel.

Dark theme, **red = up / blue = down** (Korean convention). Layout patterns are
modeled on Korean brokerage dashboards; all branding and assets are our own.

## Layout

```
app/
  main.py            FastAPI entrypoint
  config.py          Settings from .env
  api/               Routes + dependency wiring (thin)
  core/analytics.py  Sharpe, max drawdown, beta, VaR, CAGR
  data/
    providers.py     Market data behind one swappable interface
    universe.py      Tracked indices and tickers
    cache.py         TTL cache — the dashboard fans out to ~30 symbols
  models/schemas.py  Pydantic contracts
  services/          Forecasting, portfolio, dividends, news, paper trading,
                     market board, watchlist
frontend/
  src/lib/           API client, types mirroring the Pydantic schemas, polling hook
  src/components/    Sparkline, IndexGrid, MoversTable, WatchlistRail, TickerBar,
                     AllocationDonut, TickerAvatar
  src/pages/         Home (홈), Account (내 계좌)
tests/               Pure-logic tests, no network
docs/                Architecture + roadmap
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
- **The UI never claims to be live.** Quotes are ~15 min delayed and the board
  returns `stale: true`. The header says 지연 시세, not 실시간, until a paid feed
  is wired in.
- **Empty states, not error pages.** If a provider call fails, that symbol drops
  out and the rest of the board still renders.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/ROADMAP.md](docs/ROADMAP.md).
