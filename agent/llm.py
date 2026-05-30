"""
LLM Interface — clean abstraction over the actual model.
Falls back to stub automatically if:
  - No API key set
  - API key is "stub"
  - Account has no credits (BadRequestError)
  - Any other API error
"""

import json
from config import get_settings

settings = get_settings()


def _is_stub() -> bool:
    return not settings.anthropic_api_key or settings.anthropic_api_key in ("stub", "YOUR_KEY_HERE")


def call_llm(system: str, user: str) -> str:
    """
    Send a prompt to the LLM and get a text response back.
    Falls back to stub on any API error so the app never crashes.
    """
    if _is_stub():
        return _stub_response(system, user)

    try:
        import anthropic
        client  = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return message.content[0].text

    except Exception as e:
        # Log the real error but fall back gracefully
        print(f"[llm] API error — falling back to stub: {e}")
        return _stub_response(system, user)


def _stub_response(system: str, user: str) -> str:
    """
    Deterministic stub — parses the user message to extract
    commodity/location/quantity so even stub mode feels smart.
    """
    user_lower = user.lower()

    # ── Intake classification ──
    if "intent" in system.lower() or "classify" in system.lower():

        # Try to extract commodity
        commodities = ["tomato", "maize", "yam", "rice", "onion", "pepper", "cassava", "plantain"]
        commodity = next((c for c in commodities if c in user_lower), None)

        # Try to extract location
        locations = ["tamale", "accra", "kumasi", "nairobi", "lagos", "abuja", "kampala", "dar es salaam"]
        location = next((l for l in locations if l in user_lower), None)

        # Try to extract quantity
        import re
        qty_match = re.search(r'(\d+)\s*(crates?|bags?|kg|tons?|pieces?|units?|boxes?)', user_lower)
        quantity   = int(qty_match.group(1)) if qty_match else None
        qty_unit   = qty_match.group(2).rstrip('s') if qty_match else None
        if qty_unit:
            qty_unit = qty_unit + ('s' if quantity and quantity > 1 else '')

        # If nothing found — advisory
        if not commodity:
            return json.dumps({
                "intent": "advisory",
                "commodity": None,
                "location": None,
                "quantity": None,
                "quantity_unit": None
            })

        return json.dumps({
            "intent": "producer_to_market",
            "commodity": commodity,
            "location": location,
            "quantity": quantity,
            "quantity_unit": qty_unit or "units"
        })

    # ── Pricing agent ──
    # Extract the actual numbers from the prompt so stub reflects real market data
    if "price" in system.lower() or "market" in system.lower():
        import re
        low_m    = re.search(r'Low:\s*([\d.]+)\s*(\w+)', user)
        median_m = re.search(r'Median:\s*([\d.]+)', user)
        high_m   = re.search(r'High:\s*([\d.]+)', user)
        currency_m = re.search(r'Low:\s*[\d.]+\s*(\w+)', user)

        low      = float(low_m.group(1))    if low_m    else 38.0
        median   = float(median_m.group(1)) if median_m else 45.0
        high     = float(high_m.group(1))   if high_m   else 52.0
        currency = currency_m.group(1)      if currency_m else "GHS"

        rec_low  = round(median, 2)
        rec_high = round((median + high) / 2, 2)

        return json.dumps({
            "recommended_low":  rec_low,
            "recommended_high": rec_high,
            "reasoning": (
                f"Based on current market data, prices range from {low} to {high} {currency}. "
                f"I recommend {rec_low}–{rec_high} {currency} — near the median to stay competitive "
                f"while capturing above-average value given active buyer demand."
            )
        })

    return json.dumps({"response": "stub response"})