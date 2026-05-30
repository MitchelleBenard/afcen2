"""
Telemetry Utility

Emits anonymised events to the mock signal API.
Called at key moments: price proposed, approval resolved.

Personal data is stripped before sending — only market signals go out.
"""

import httpx
from datetime import datetime, timezone
from helper import anonymise
from config import get_settings

settings = get_settings()


def emit_event(event_type: str, payload: dict) -> None:
    """
    Fire-and-forget telemetry. Never raises — a failed emit should never
    break the builder's experience.
    """
    safe_payload = anonymise(payload)

    body = {
        "event_type": event_type,
        "payload": safe_payload,
        "emitted_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        httpx.post(settings.signal_api_url, json=body, timeout=3.0)
    except Exception as e:
        # Log silently — telemetry is best-effort
        print(f"[telemetry] failed to emit {event_type}: {e}")
