# AI Stock Trader

Equity research toolkit: price projections from historical data, portfolio and
dividend analytics, news sentiment signals, and a paper-trading simulator.

> **Research tool, not advice.** Every number here is a statistical projection
> from historical data. The app never connects to a broker and never places a
> real order. Nothing in it is investment advice.

## Quick start

```bash
cd ai-stock-trader
./start.sh
```

That's it. On a fresh clone it creates the virtualenv, installs both dependency
sets, then runs the API and the dashboard together with output prefixed `[api]`
and `[web]`. The browser opens once Vite is listening; Ctrl+C stops both.

- Dashboard: http://localhost:5173
- API docs: http://127.0.0.1:8000/docs

Run `NO_OPEN=1 ./start.sh` to skip the browser launch.

Vite proxies `/api` to the backend, so there's no CORS setup in dev.

To run just the API: `bash scripts/dev.sh`.

**Don't run bare `uvicorn app.main:app --reload`.** Plain `--reload` also
watches `.venv/`, and site-packages churns enough on macOS to restart the server
every few seconds — which drops the price stream, clears the board cache, and
refetches every symbol each time until Yahoo rate-limits you. Both scripts pass
`--reload-dir app` so only your own code triggers a restart.

### Tests

```bash
.venv/bin/pytest && .venv/bin/ruff check .   # backend
cd frontend && npm run build                 # frontend typecheck + bundle
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
| Live prices | `WS /api/v1/ws/prices` | Pushed ticks from Yahoo's streamer |
| Stream health | `GET /api/v1/market/stream/status` | Which symbols are live vs. delayed |

## Live prices

The app holds one WebSocket open to `wss://streamer.finance.yahoo.com` — the
same feed finance.yahoo.com uses — and fans ticks out to browsers over its own
socket. However many tabs are open, there is exactly one upstream connection.

REST still supplies the slow-moving columns (volume, market cap, prior close);
the stream only overrides price and change. Symbols the streamer doesn't
deliver, typically Korean listings, fall back to a 15-second poll and are
labeled 지연 rather than 실시간.

Caveat: the streamer is an undocumented endpoint. It can change without notice.
If ticks stop, `GET /api/v1/market/stream/status` shows what's still live.

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
