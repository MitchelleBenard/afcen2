"""
Ventures Route

GET  /ventures/{venture_id}         → fetch a venture
POST /ventures/{venture_id}/price   → trigger the pricing agent
"""

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from database import get_db
from app.models import Venture, Offer, Approval, ApprovalStatus
from app.schemas import VentureResponse, PriceProposalResponse
from agent.pricing_agent import propose_price
from app.utils.telemetry import emit_event

router = APIRouter(prefix="/ventures", tags=["Ventures"])


@router.get("/{venture_id}", response_model=VentureResponse)
def get_venture(venture_id: str, db: Session = Depends(get_db)):
    venture = db.query(Venture).filter(Venture.id == venture_id).first()
    if not venture:
        raise HTTPException(status_code=404, detail="Venture not found")
    return venture


@router.post("/{venture_id}/price", response_model=PriceProposalResponse, status_code=201)
def request_price_proposal(venture_id: str, db: Session = Depends(get_db)):
    """
    Trigger the pricing agent for this venture.
    The agent fetches market data, reasons over it, and creates a PENDING approval.
    Nothing is committed until the builder approves at POST /approvals/{approval_id}.
    """

    # 1. Load the venture
    venture = db.query(Venture).filter(Venture.id == venture_id).first()
    if not venture:
        raise HTTPException(status_code=404, detail="Venture not found")

    if not venture.commodity or not venture.location:
        raise HTTPException(
            status_code=422,
            detail="Venture needs a commodity and location before pricing. Re-run intake with more detail."
        )

    # 2. Run the pricing agent
    proposal = propose_price(
        commodity=venture.commodity,
        location=venture.location,
        quantity=venture.quantity or 0,
        quantity_unit=venture.quantity_unit or "units",
    )

    # 3. Save the proposal as a PENDING Approval — not yet applied
    proposed_value = json.dumps({
        "price_low": proposal["recommended_low"],
        "price_high": proposal["recommended_high"],
        "currency": proposal.get("currency", "GHS"),
    })

    approval = Approval(
        venture_id=venture_id,
        action_type="set_price",
        proposed_value=proposed_value,
        agent_reasoning=proposal["reasoning"],
        status=ApprovalStatus.PENDING,
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)

    # 4. Emit telemetry — agent proposed a price (anonymised)
    emit_event("agent.price_proposed", {
        "venture_id": venture_id,
        "builder_id": venture.builder_id,
        "commodity": venture.commodity,
        "location": venture.location,
        "proposed_low": proposal["recommended_low"],
        "proposed_high": proposal["recommended_high"],
    })

    return PriceProposalResponse(
        approval_id=approval.id,
        venture_id=venture_id,
        action_type="set_price",
        proposed_low=proposal["recommended_low"],
        proposed_high=proposal["recommended_high"],
        currency=proposal.get("currency", "GHS"),
        reasoning=proposal["reasoning"],
        market_data_summary=proposal["market_data_summary"],
        status=ApprovalStatus.PENDING,
    )