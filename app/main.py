"""FastAPI entrypoint.

Run locally:  uvicorn app.main:app --reload
Docs:         http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings
from app.services import streaming

settings = get_settings()
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)

@asynccontextmanager
async def lifespan(_: FastAPI):
    # No separate prewarm: the streamer's board loop refreshes immediately on
    # start, so a second warm-up task just doubled the boot-time fetch.
    await streaming.streamer.start()
    yield
    await streaming.streamer.stop()


app = FastAPI(
    title="AI Stock Trader",
    version="0.1.0",
    lifespan=lifespan,
    description=(
        "Equity research toolkit: price projections, portfolio and dividend analytics, "
        "news sentiment, and paper trading. Research tool only — not investment advice, "
        "and it never places real orders."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}
