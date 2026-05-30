"""
Approvals Route

POST /approvals/{approval_id}

The builder approves, rejects, or edits an agent proposal.
Only after approval does real state change — offer price gets set.
"""

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from database import get_db
from app.models import Approval, Offer, Venture, ApprovalStatus, VentureStatus
from app.schemas import ApprovalRequest, ApprovalResponse
from app.utils.telemetry import emit_event
from helper import now_utc

router = APIRouter(prefix="/approvals", tags=["Approvals"])


@router.post("/{approval_id}", response_model=ApprovalResponse)
def resolve_approval(
    approval_id: str,
    payload: ApprovalRequest,
    db: Session = Depends(get_db),
):
    """
    Builder decides on an agent proposal.

    - 'approve'  → apply the agent's proposed value
    - 'reject'   → mark rejected, nothing changes
    - 'edit'     → apply builder's edited_value instead
    """

    # 1. Load the approval
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=409,
            detail=f"Approval already resolved with status: {approval.status}"
        )

    decision = payload.decision.lower().strip()
    if decision not in ("approve", "reject", "edit"):
        raise HTTPException(status_code=422, detail="Decision must be 'approve', 'reject', or 'edit'")

    if decision == "edit" and payload.edited_value is None:
        raise HTTPException(status_code=422, detail="edited_value required when decision is 'edit'")

    # 2. Load the related venture
    venture = db.query(Venture).filter(Venture.id == approval.venture_id).first()

    final_price = None

    if decision == "reject":
        approval.status = ApprovalStatus.REJECTED
        approval.resolved_at = now_utc()
        message = "Proposal rejected. No changes made."

    elif decision in ("approve", "edit"):
        proposed = json.loads(approval.proposed_value or "{}")

        if decision == "approve":
            final_price = proposed.get("price_low")  # Use the low as the set price
            approval.status = ApprovalStatus.APPROVED
        else:
            final_price = payload.edited_value
            approval.builder_value = str(final_price)
            approval.status = ApprovalStatus.EDITED

        approval.resolved_at = now_utc()

        # 3. Apply the price to the Offer
        if approval.action_type == "set_price" and venture:
            offer = db.query(Offer).filter(Offer.venture_id == venture.id).first()
            if offer:
                offer.price_low = proposed.get("price_low")
                offer.price_high = proposed.get("price_high")
                offer.price_set = final_price

            # Activate the venture
            venture.status = VentureStatus.ACTIVE

        message = f"{'Price approved' if decision == 'approve' else 'Price edited and approved'} at GHS {final_price:.2f} per unit. Venture is now active."

        # 4. Emit telemetry
        emit_event("builder.approval_resolved", {
            "approval_id": approval_id,
            "venture_id": approval.venture_id,
            "builder_id": venture.builder_id if venture else None,
            "decision": decision,
            "final_price": final_price,
            "commodity": venture.commodity if venture else None,
            "location": venture.location if venture else None,
        })

    db.commit()

    return ApprovalResponse(
        approval_id=approval_id,
        venture_id=approval.venture_id,
        status=approval.status,
        final_price=final_price,
        message=message,
    )
