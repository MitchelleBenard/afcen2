from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Anthropic — paste your key directly here
    anthropic_api_key: str = "put key here"

    # Mock Signal API (telemetry sink)
    signal_api_url: str = "http://localhost:8001/v1/ingest"

    # Mock Market API
    market_api_url: str = "http://localhost:8001/v1/market-prices"
    demand_api_url: str = "http://localhost:8001/v1/demand-signals"
    weather_api_url: str = "http://localhost:8001/v1/weather"

    # App
    app_name: str = "AfCEN Venture Platform"
    debug: bool = True

    class Config:
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()