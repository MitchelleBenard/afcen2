"""
Intake Route — conversational, asks follow-up questions when info is missing.
"""

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from app.models import Builder, Venture, Offer, IntentType
from app.schemas import IntakeRequest, IntakeResponse
from agent.llm import call_llm

router = APIRouter(prefix="/intake", tags=["Intake"])


def _classify_message(message: str) -> dict:
    system_prompt = """You are an intake classifier for a venture platform serving African small business owners.

Extract structured information from the builder's message.

If the message is a greeting, question, or does not describe a business or product to sell,
return intent as "advisory" and leave commodity, location, quantity, quantity_unit as null.

Respond ONLY with a JSON object in this exact shape (no markdown, no extra text, no explanation):
{
  "intent": "<one of: producer_to_market, aggregation, local_service, advisory>",
  "commodity": "<what they are selling, lowercase, or null>",
  "location": "<city or region, lowercase, or null>",
  "quantity": <integer or null>,
  "quantity_unit": "<e.g. crates, bags, kg, or null>"
}"""

    raw = call_llm(system=system_prompt, user=f'Builder message: "{message}"')

    try:
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(clean)
    except Exception:
        return {"intent": "advisory", "commodity": None, "location": None, "quantity": None, "quantity_unit": None}


def _build_followup(commodity, location, quantity, quantity_unit) -> str | None:
    """
    If any required field is missing, return a friendly follow-up question.
    Returns None if we have everything we need.
    """
    missing = []

    if not location:
        missing.append("📍 **Where are you located?** (e.g. Tamale, Accra, Nairobi)")

    if not quantity or not quantity_unit:
        missing.append("📦 **How much do you have?** (e.g. 80 crates, 20 bags, 100 kg)")

    if not missing:
        return None

    intro = f"I can see you have **{commodity}** to sell — great! I just need a couple more details to give you a price:"
    return intro + "\n\n" + "\n\n".join(missing)


@router.post("/", response_model=IntakeResponse, status_code=201)
def intake(payload: IntakeRequest, db: Session = Depends(get_db)):

    # 1. Builder must exist
    builder = db.query(Builder).filter(Builder.id == payload.builder_id).first()
    if not builder:
        raise HTTPException(status_code=404, detail=f"Builder '{payload.builder_id}' not found.")

    # 2. Classify
    classified = _classify_message(payload.message)

    try:
        intent = IntentType(classified.get("intent", "advisory"))
    except ValueError:
        intent = IntentType.ADVISORY

    commodity    = classified.get("commodity")
    location     = classified.get("location")
    quantity     = classified.get("quantity")
    quantity_unit = classified.get("quantity_unit")

    # 3. Pure greeting / no business info at all
    if not commodity:
        return IntakeResponse(
            venture_id="none",
            intent=IntentType.ADVISORY,
            commodity=None, location=None, quantity=None, quantity_unit=None,
            status="draft",
            message=(
                "Hello! I'm the AfCEN venture assistant. 👋\n\n"
                "Tell me about your business — what you're selling, where you are, and how much you have.\n\n"
                "For example: *\"I have 80 crates of tomatoes in Tamale, what should I charge?\"*"
            ),
        )

    # 4. Has commodity but missing location or quantity — ask follow-up
    followup = _build_followup(commodity, location, quantity, quantity_unit)
    if followup:
        return IntakeResponse(
            venture_id="none",
            intent=intent,
            commodity=commodity,
            location=location,
            quantity=quantity,
            quantity_unit=quantity_unit,
            status="draft",
            message=followup,
        )

    # 5. We have everything — create the venture
    venture = Venture(
        builder_id=payload.builder_id,
        raw_message=payload.message,
        intent=intent,
        commodity=commodity,
        location=location,
        quantity=quantity,
        quantity_unit=quantity_unit,
    )
    db.add(venture)
    db.flush()

    offer = Offer(
        venture_id=venture.id,
        commodity=commodity,
        quantity=quantity,
        quantity_unit=quantity_unit,
    )
    db.add(offer)
    db.commit()
    db.refresh(venture)

    parts = []
    if quantity and quantity_unit:
        parts.append(f"{quantity} {quantity_unit} of {commodity}")
    elif commodity:
        parts.append(commodity)
    if location:
        parts.append(f"in {location}")

    summary = f"Got it! I understood you have {' '.join(parts)}. Your venture has been created."

    return IntakeResponse(
        venture_id=venture.id,
        intent=venture.intent,
        commodity=venture.commodity,
        location=venture.location,
        quantity=venture.quantity,
        quantity_unit=venture.quantity_unit,
        status=venture.status,
        message=summary,
    )