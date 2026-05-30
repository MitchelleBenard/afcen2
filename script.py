"""
Demo Script — Full Tomato Scenario

Walks through the complete flow end-to-end:
  1. Create a builder (Ama)
  2. Send her message to intake
  3. Trigger the pricing agent
  4. Approve the proposal
  5. Verify final state

Run with: python script.py
The main app must be running on port 8000.
The mock signal API must be running on port 8001.
"""

import httpx
import json
import sys

BASE = "http://localhost:8000"


def step(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def show(label: str, data: dict):
    print(f"\n{label}:")
    print(json.dumps(data, indent=2))


def run():
    client = httpx.Client(base_url=BASE, timeout=15.0)

    # ── Step 1: Create Ama as a builder ───────────────────────────────────────
    step("STEP 1 — Register Builder (Ama)")
    r = client.post("/builders/", json={"name": "Ama Asante"})
    assert r.status_code == 201, f"Failed: {r.text}"
    builder = r.json()
    show("Builder created", builder)
    builder_id = builder["id"]

    # ── Step 2: Intake — Ama's message ────────────────────────────────────────
    step("STEP 2 — Intake (Ama's message)")
    message = "I have 80 crates of tomatoes in Tamale, what should I charge?"
    print(f'\nAma says: "{message}"')

    r = client.post("/intake/", json={"builder_id": builder_id, "message": message})
    assert r.status_code == 201, f"Failed: {r.text}"
    intake = r.json()
    show("Intake result", intake)
    venture_id = intake["venture_id"]

    print(f"\n✅ Venture created: {venture_id}")
    print(f"   Intent   : {intake['intent']}")
    print(f"   Commodity: {intake['commodity']}")
    print(f"   Location : {intake['location']}")
    print(f"   Quantity : {intake['quantity']} {intake['quantity_unit']}")

    # ── Step 3: Trigger pricing agent ─────────────────────────────────────────
    step("STEP 3 — Pricing Agent Proposes a Price")
    r = client.post(f"/ventures/{venture_id}/price")
    assert r.status_code == 201, f"Failed: {r.text}"
    proposal = r.json()
    show("Agent proposal", proposal)
    approval_id = proposal["approval_id"]

    print(f"\n💡 Agent suggests: GHS {proposal['proposed_low']} – {proposal['proposed_high']} per crate")
    print(f"\n📋 Reasoning: {proposal['reasoning']}")
    print(f"\n⏳ Status: {proposal['status']} — waiting for Ama's approval")

    # ── Step 4: Ama approves ───────────────────────────────────────────────────
    step("STEP 4 — Builder Approves the Price")
    print("\nAma reviews the proposal and approves...")

    r = client.post(f"/approvals/{approval_id}", json={"decision": "approve"})
    assert r.status_code == 200, f"Failed: {r.text}"
    approval = r.json()
    show("Approval result", approval)

    print(f"\n✅ {approval['message']}")

    # ── Step 5: Verify final venture state ────────────────────────────────────
    step("STEP 5 — Verify Final Venture State")
    r = client.get(f"/ventures/{venture_id}")
    assert r.status_code == 200, f"Failed: {r.text}"
    venture = r.json()
    show("Final venture", venture)

    print(f"\n🎉 Done! Venture status: {venture['status']}")
    print("\nFull flow completed successfully.")
    print("Check the mock signal API terminal for telemetry events.")


if __name__ == "__main__":
    try:
        run()
    except httpx.ConnectError:
        print("\n❌ Could not connect to the app.")
        print("Make sure both servers are running:")
        print("  Terminal 1: uvicorn main:app --reload")
        print("  Terminal 2: uvicorn mock_signal_api.server:app --port 8001 --reload")
        sys.exit(1)
    except AssertionError as e:
        print(f"\n❌ Step failed: {e}")
        sys.exit(1)
