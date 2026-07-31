"""Application settings, loaded from environment / .env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"

    market_data_provider: str = "yfinance"
    alpha_vantage_api_key: str = ""
    polygon_api_key: str = ""

    newsapi_key: str = ""
    finnhub_api_key: str = ""
    anthropic_api_key: str = ""

    data_dir: Path = ROOT / "data" / "store"
    cache_dir: Path = ROOT / "data" / "cache"
    cache_ttl_seconds: int = 900

    paper_starting_cash: float = 100_000.0

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
