# Design Note — AfCEN Venture Platform

## What I Built and Why

The brief asked for a backend slice of an agentic venture platform — specifically the intake-to-approval loop for a small-scale producer. I focused on making this loop clean, well-reasoned, and fully demoable rather than partially implementing more features.

---

## Data Model

Four tables, intentionally minimal:

**Builder** — the human using the platform. Every piece of data is scoped to a Builder. This is the tenant boundary.

**Venture** — the core object. One business a builder is running. Stores what the AI understood from the builder's plain-language message: commodity, location, quantity, intent. Status moves from `draft` → `active` after a price is approved.

**Offer** — what the venture is selling, with price fields. `price_low` and `price_high` come from the agent's proposal. `price_set` is only filled after the builder approves — it's the single source of truth for the committed price.

**Approval** — the human-in-the-loop gate. Every consequential agent action creates a `PENDING` Approval first. The builder resolves it (`approved`, `rejected`, `edited`). Only then does `Offer.price_set` change and `Venture.status` advance. The agent cannot bypass this.

This model makes the approval audit trail first-class — every pricing decision is traceable.

---

## Agent Design

The pricing agent follows a simple, readable pipeline:

```
Venture (commodity, location, quantity)
    → fetch market prices   (mock API)
    → fetch demand signals  (mock API)
    → fetch weather         (mock API)
    → build context string
    → call LLM with structured prompt
    → parse JSON response
    → return proposal (not saved yet)
```

The agent only *proposes*. It has no write access to the database. The route layer saves the `Approval` record, and the approval route applies the change only after the builder says yes.

**LLM Interface (`agent/llm.py`)** — the rest of the codebase never imports `anthropic` directly. The interface is a single `call_llm(system, user) -> str` function. Swapping to GPT-4, Gemini, or a stub is a one-line change. The stub returns deterministic JSON responses, which means the full flow is testable with zero API costs.

---

## Stretch Item: Clean Tool/Permission Layer

Rather than adding multi-agent orchestration (which would have been partially done), I chose the tooling/guardrails stretch because it reinforces the CORE:

- **LLM abstraction** — swappable, stub-first, no vendor lock-in
- **Telemetry** — fire-and-forget, never breaks the user path, strips PII before sending
- **Input validation** — Pydantic schemas reject malformed requests at the boundary; the agent checks that commodity and location exist before running
- **Approval gate is enforced structurally** — there is no code path that sets `Offer.price_set` without a resolved Approval record

---

## Tradeoffs

**SQLite over PostgreSQL** — sufficient for a demo and zero setup friction. The SQLAlchemy abstraction means swapping to Postgres is a one-line change to `DATABASE_URL`.

**No async** — FastAPI supports async, but the LLM and HTTP calls here are synchronous. For production I'd move `call_llm` and `httpx` calls to async to avoid blocking the event loop under load.

**Builder ID passed by caller** — no auth in scope per brief. In production this would come from a JWT.

**Single pricing agent** — the brief asks for one. The pipeline is designed to be extended: add a `listing_agent.py` that proposes a market listing, gate it behind another Approval, same pattern.

---

## Security Notes

- API key loaded from environment, never hardcoded
- Builder ID in telemetry is SHA-256 hashed (first 16 chars) — AfCEN can count unique builders without knowing who they are
- `raw_message` (personal text) is stripped from telemetry entirely
- Approval gate means the agent cannot take any action that affects a builder's business without explicit consent

---

## What I'd Build Next

1. **Auth** — JWT with builder_id claim, remove it from request bodies
2. **Async** — move LLM and HTTP calls to `asyncio` for production throughput
3. **Evals** — test cases for the intake classifier: does it correctly extract commodity/location/quantity across different phrasings? Especially important for non-standard English and local phrasing (e.g. "I get 80 boxes tomatoes for Tamale")
4. **Second flow** — aggregator intake: a trader buying from multiple producers, with a different price logic (buy low, not sell high)
5. **Retry/fallback** — if the LLM returns unparseable JSON, retry once with a stricter prompt before falling back to the market median
