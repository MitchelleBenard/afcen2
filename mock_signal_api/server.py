"""
Mock External APIs — runs as a separate server on port 8001.

This simulates:
  - GET  /v1/market-prices    → price bands for a commodity
  - GET  /v1/demand-signals   → active buyers in a market
  - GET  /v1/weather          → forecast + risk flag
  - POST /v1/ingest           → telemetry sink (just prints and acks)

Run with: uvicorn mock_signal_api.server:app --port 8001
"""

from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import Any
from datetime import datetime, timezone
import random

app = FastAPI(title="AfCEN Mock APIs", version="1.0.0")


# ── Market Prices ──────────────────────────────────────────────────────────────


PRICE_DATA = {
    "tomato": {
        "nairobi":  {"low": 100.0, "median": 150.0, "high": 200.0, "currency": "KES", "unit": "bags"},
        "tamale":   {"low": 38.0, "median": 45.0, "high": 52.0, "currency": "GHS", "unit": "crate"},
        "accra":    {"low": 50.0, "median": 60.0, "high": 72.0, "currency": "GHS", "unit": "crate"},
        "kumasi":   {"low": 42.0, "median": 48.0, "high": 56.0, "currency": "GHS", "unit": "crate"},
        "default":  {"low": 40.0, "median": 47.0, "high": 55.0, "currency": "GHS", "unit": "crate"},
    },
    "maize": {
        "tamale":   {"low": 200.0, "median": 240.0, "high": 280.0, "currency": "GHS", "unit": "bag"},
        "default":  {"low": 190.0, "median": 230.0, "high": 270.0, "currency": "GHS", "unit": "bag"},
    },
    "yam": {
        "default":  {"low": 15.0, "median": 22.0, "high": 30.0, "currency": "GHS", "unit": "tuber"},
    },
}


@app.get("/v1/market-prices")
def get_market_prices(
    commodity: str = Query(..., description="e.g. tomato, maize, yam"),
    market: str = Query("default", description="e.g. tamale, accra, kumasi"),
):
    commodity = commodity.lower()
    market = market.lower()

    commodity_data = PRICE_DATA.get(commodity, PRICE_DATA.get("tomato"))
    price = commodity_data.get(market, commodity_data.get("default"))

    return {
        "commodity": commodity,
        "market": market,
        "prices": price,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "source": "mock-market-data-v1",
    }


# ── Demand Signals ─────────────────────────────────────────────────────────────

DEMAND_DATA = {
    "tamale": [
        {"buyer_type": "restaurant", "volume_needed": 20, "unit": "crates", "urgency": "high"},
        {"buyer_type": "wholesaler", "volume_needed": 50, "unit": "crates", "urgency": "medium"},
    ],
    "accra": [
        {"buyer_type": "supermarket", "volume_needed": 100, "unit": "crates", "urgency": "medium"},
    ],
    "default": [
        {"buyer_type": "local_market", "volume_needed": 30, "unit": "crates", "urgency": "low"},
    ],
}


@app.get("/v1/demand-signals")
def get_demand_signals(
    commodity: str = Query(...),
    market: str = Query("default"),
):
    market = market.lower()
    buyers = DEMAND_DATA.get(market, DEMAND_DATA["default"])

    return {
        "commodity": commodity,
        "market": market,
        "active_buyers": buyers,
        "total_demand_units": sum(b["volume_needed"] for b in buyers),
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


# ── Weather ────────────────────────────────────────────────────────────────────

@app.get("/v1/weather")
def get_weather(location: str = Query("tamale")):
    location = location.lower()

    # Simplified mock — in reality this would call a weather service
    forecasts = {
        "tamale":  {"condition": "sunny", "temp_c": 34, "risk_flag": False, "advisory": "Good conditions for transport"},
        "accra":   {"condition": "partly_cloudy", "temp_c": 28, "risk_flag": False, "advisory": "Normal conditions"},
        "kumasi":  {"condition": "rain_expected", "temp_c": 24, "risk_flag": True,  "advisory": "Heavy rain may affect road transport — consider delay"},
    }

    forecast = forecasts.get(location, {"condition": "unknown", "temp_c": 30, "risk_flag": False, "advisory": "No data"})

    return {
        "location": location,
        "forecast": forecast,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


# ── Telemetry Sink ─────────────────────────────────────────────────────────────

class TelemetryEvent(BaseModel):
    event_type: str
    payload: dict[str, Any]
    emitted_at: str


@app.post("/v1/ingest", status_code=202)
def ingest_telemetry(event: TelemetryEvent):
    """
    Receives anonymised telemetry events from the main app.
    In production this would stream to a data warehouse.
    Here we just print and acknowledge.
    """
    print(f"\n📡 TELEMETRY RECEIVED")
    print(f"   event : {event.event_type}")
    print(f"   data  : {event.payload}")
    print(f"   at    : {event.emitted_at}\n")

    return {"status": "accepted", "event_type": event.event_type}
