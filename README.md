# AfCEN Venture Platform — Take-Home Assessment

A small backend slice of an agentic venture operating platform for African builders.
A builder describes their business in plain language, an AI agent helps price their goods, and the builder approves before anything is committed.

---

## What's Built

### Core (all complete)
- **Conversational Intake** — plain language message → structured Venture profile via LLM
- **Venture Persistence** — SQLite via SQLAlchemy, survives restarts
- **Pricing Agent** — fetches mock market, demand, and weather data; reasons over it with Claude; proposes a price range
- **Human Approval Gate** — agent proposes, builder approves/rejects/edits; only then does state change
- **Anonymised Telemetry** — key events emitted to mock ingest endpoint, builder ID hashed, no personal data

### Stretch (clean tool/permission layer)
- LLM is behind a clean interface (`agent/llm.py`) — swappable between Claude and a deterministic stub
- Stub mode works with no API key — positive signal for testability
- Telemetry is fire-and-forget — never breaks the builder experience

---

## Project Structure

```
afcen/
├── app/
│   ├── models/
│   │   └── venture.py       # Builder, Venture, Offer, Approval tables + enums
│   ├── routes/
│   │   ├── builders.py      # POST /builders, GET /builders/{id}
│   │   ├── intake.py        # POST /intake — classify message, create Venture
│   │   ├── ventures.py      # GET /ventures/{id}, POST /ventures/{id}/price
│   │   └── approvals.py     # POST /approvals/{id} — approve/reject/edit
│   ├── schemas/
│   │   ├── intake.py        # IntakeRequest, IntakeResponse
│   │   ├── venture.py       # VentureResponse, BuilderCreate, BuilderResponse
│   │   └── approval.py      # PriceProposalResponse, ApprovalRequest, ApprovalResponse
│   └── utils/
│       └── telemetry.py     # emit_event — anonymised fire-and-forget
├── agent/
│   ├── llm.py               # LLM interface — Claude or stub
│   └── pricing_agent.py     # Fetches market data, calls LLM, returns proposal
├── mock_signal_api/
│   └── server.py            # Mock market prices, demand, weather, telemetry sink
├── config.py                # Settings loaded from .env
├── database.py              # SQLite engine + get_db dependency
├── helper.py                # anonymise(), now_utc(), safe_json()
├── main.py                  # FastAPI app + table creation on startup
├── script.py                # End-to-end demo (the tomato scenario)
├── requirements.txt
└── .env
```

---

## Setup

## Prerequisites
Python 3.11+
Git
pip

Verify installation:

### Windows
```powershell
python --version
pip --version
git --version
```

### linux
```bash
python3 --version
pip3 --version
git --version
```

### 1. Clone and install
### windows

```powershell
git clone <repo-url>
cd afcen
pip install -r requirements.txt
```

### linux
```bash
git clone <repo-url>
cd afcen
pip install -r requirements.txt
```

### 2. Configure environment

### windows
```
powershell
python -m venv venv
venv\Scripts\activate
```
### linux
```
bash
cp .env .env.local
# Edit .env and set your ANTHROPIC_API_KEY
# Leave it as "stub" to run without an API key (uses deterministic stub responses)
```

### 3. Run the mock Signal/Market API (Terminal 1)

### windows
```powershell
uvicorn mock_signal_api.server:app --port 8001 --reload
```

### linux
```bash
uvicorn mock_signal_api.server:app --port 8001 --reload
```

### 4. Run the main app (Terminal 2)

### windows
```powershell
uvicorn main:app --reload
```

### linux
```bash
uvicorn main:app --reload
```

The database (`afcen.db`) is created automatically on first run.
API docs available at: **http://localhost:8000/docs**

### 5. Run the demo (Terminal 3)
### windows
```powershell
python script.py
```

### linux
```bash
python script.py
```

This walks the full tomato scenario from start to finish and prints each step.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/builders/` | Register a new builder |
| GET | `/builders/{id}` | Get builder details |
| POST | `/intake/` | Submit a plain language message, creates Venture |
| GET | `/ventures/{id}` | Get venture details |
| POST | `/ventures/{id}/price` | Trigger pricing agent → creates PENDING approval |
| POST | `/approvals/{id}` | Builder approves / rejects / edits agent proposal |

---

## The Tomato Scenario (manual)

```bash
# 1. Create a builder
curl -X POST http://localhost:8000/builders/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Ama Asante"}'

# 2. Submit her message (use the builder id from step 1)
curl -X POST http://localhost:8000/intake/ \
  -H "Content-Type: application/json" \
  -d '{"builder_id": "<builder_id>", "message": "I have 80 crates of tomatoes in Tamale, what should I charge?"}'

# 3. Trigger the pricing agent (use venture_id from step 2)
curl -X POST http://localhost:8000/ventures/<venture_id>/price

# 4. Approve the proposal (use approval_id from step 3)
curl -X POST http://localhost:8000/approvals/<approval_id> \
  -H "Content-Type: application/json" \
  -d '{"decision": "approve"}'
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | `stub` | Claude API key. If unset or "stub", uses deterministic stub |
| `SIGNAL_API_URL` | `http://localhost:8001/v1/ingest` | Telemetry sink |
| `MARKET_API_URL` | `http://localhost:8001/v1/market-prices` | Mock market prices |
| `DEMAND_API_URL` | `http://localhost:8001/v1/demand-signals` | Mock demand signals |
| `WEATHER_API_URL` | `http://localhost:8001/v1/weather` | Mock weather API |

---
