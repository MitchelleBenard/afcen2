import hashlib
import json
from datetime import datetime, timezone


def anonymise(data: dict) -> dict:
    """
    Strip personal identifiers from a dict before sending to telemetry.
    - builder_id is hashed (so we can count unique builders without knowing who they are)
    - name fields are dropped entirely
    - location is kept (it's market data, not personal)
    """
    safe = {}
    for key, value in data.items():
        if key in ("name", "raw_message"):
            continue  # Drop — too personal
        if key == "builder_id" and value:
            # One-way hash — AfCEN can count unique builders but can't reverse it
            safe[key] = hashlib.sha256(str(value).encode()).hexdigest()[:16]
        else:
            safe[key] = value
    return safe


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def safe_json(value: str) -> dict:
    """Parse a JSON string safely, return empty dict on failure"""
    try:
        return json.loads(value)
    except Exception:
        return {}
