"""
Pricing Agent

Fetches market data, reasons over it with the LLM, and proposes a price.
Resilient — if the mock API is down, uses sensible fallback data.
"""

import httpx
import json
from agent.llm import call_llm
from config import get_settings

settings = get_settings()

# Fallback data used when the mock API is unreachable
FALLBACK_PRICES = {
    "low": 38.0, "median": 45.0, "high": 52.0, "currency": "GHS", "unit": "unit"
}
FALLBACK_BUYERS = [
    {"buyer_type": "local_market", "volume_needed": 30, "urgency": "medium"}
]


def _fetch_market_data(commodity: str, location: str) -> dict:
    try:
        r = httpx.get(
            settings.market_api_url,
            params={"commodity": commodity, "market": location},
            timeout=3.0,
        )
        return r.json()
    except Exception:
        return {"prices": FALLBACK_PRICES, "source": "fallback"}


def _fetch_demand_signals(commodity: str, location: str) -> dict:
    try:
        r = httpx.get(
            settings.demand_api_url,
            params={"commodity": commodity, "market": location},
            timeout=3.0,
        )
        return r.json()
    except Exception:
        return {"active_buyers": FALLBACK_BUYERS, "total_demand_units": 30}


def _fetch_weather(location: str) -> dict:
    try:
        r = httpx.get(
            settings.weather_api_url,
            params={"location": location},
            timeout=3.0,
        )
        return r.json()
    except Exception:
        return {"forecast": {"condition": "unknown", "risk_flag": False, "advisory": "No data"}}


def propose_price(commodity: str, location: str, quantity: int, quantity_unit: str) -> dict:
    """
    Main agent entry point. Returns a dict with:
      - recommended_low, recommended_high, reasoning, market_data_summary
    """

    # Step 1: Gather data (gracefully handles mock API being down)
    market  = _fetch_market_data(commodity, location)
    demand  = _fetch_demand_signals(commodity, location)
    weather = _fetch_weather(location)

    prices   = market.get("prices", FALLBACK_PRICES)
    buyers   = demand.get("active_buyers", FALLBACK_BUYERS)
    forecast = weather.get("forecast", {})

    # Step 2: Build market summary
    using_fallback = market.get("source") == "fallback"
    market_summary_lines = [
        f"Market prices in {location} for {commodity}:",
        f"  Low: {prices.get('low')} {prices.get('currency', 'GHS')} per {prices.get('unit', quantity_unit)}",
        f"  Median: {prices.get('median')} {prices.get('currency', 'GHS')}",
        f"  High: {prices.get('high')} {prices.get('currency', 'GHS')}",
        f"Active buyers: {len(buyers)} ({', '.join(b['buyer_type'] for b in buyers)})",
        f"Total buyer demand: {demand.get('total_demand_units', '?')} {quantity_unit}",
        f"Weather: {forecast.get('condition', 'unknown')} — {forecast.get('advisory', '')}",
        f"Transport risk: {'YES' if forecast.get('risk_flag') else 'NO'}",
    ]
    if using_fallback:
        market_summary_lines.append("(Note: using fallback data — mock market API not running)")
    market_summary = "\n".join(market_summary_lines)

    # Step 3: Use market data directly as a baseline for the recommendation
    # The LLM adds reasoning on top — but if it's a stub, we compute from real data
    median = prices.get("median", 45.0)
    high   = prices.get("high", 52.0)
    recommended_low  = round(median, 2)
    recommended_high = round((median + high) / 2, 2)

    # Step 4: Ask the LLM to reason (it may override the numbers above)
    system_prompt = """You are a pricing advisor for small-scale African producers and traders.
Given market data, demand signals, and weather context, recommend a fair price range.

Respond ONLY with a JSON object in this exact shape (no markdown, no extra text):
{
  "recommended_low": <float>,
  "recommended_high": <float>,
  "reasoning": "<plain English explanation for the builder, 2-3 sentences>"
}"""

    user_prompt = f"""The builder has {quantity} {quantity_unit} of {commodity} in {location}.

{market_summary}

What price range should they charge per {quantity_unit}?"""

    raw = call_llm(system=system_prompt, user=user_prompt)

    # Step 4: Parse safely
    try:
        clean  = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        result = json.loads(clean)
    except Exception:
        result = {
            "recommended_low":  recommended_low,
            "recommended_high": recommended_high,
            "reasoning": f"Based on market data in {location}, {commodity} trades between {prices.get('low')} and {prices.get('high')} {prices.get('currency','GHS')}. I recommend pricing at {recommended_low}–{recommended_high} {prices.get('currency','GHS')} per {prices.get('unit', quantity_unit)}, near the median to stay competitive.",
        }

    result["market_data_summary"] = market_summary
    result["currency"] = prices.get("currency", "GHS")  # from market data, not hardcoded
    result["raw_market"] = market
    result["raw_demand"] = demand
    return result