from pydantic import BaseModel, Field
from typing import Optional
from app.models import ApprovalStatus


class PriceProposalResponse(BaseModel):
    """Returned when agent proposes a price — waiting for builder approval"""
    approval_id: str
    venture_id: str
    action_type: str
    proposed_low: float
    proposed_high: float
    currency: str
    reasoning: str            # Plain English for the builder
    market_data_summary: str  # What the market API said, summarised
    status: ApprovalStatus


class ApprovalRequest(BaseModel):
    """Builder's decision on an agent proposal"""
    decision: str = Field(..., description="'approve', 'reject', or 'edit'")
    edited_value: Optional[float] = Field(None, description="Builder's price if decision is 'edit'")

    model_config = {"json_schema_extra": {
        "example": {"decision": "approve", "edited_value": None}
    }}


class ApprovalResponse(BaseModel):
    """Result after builder decides"""
    approval_id: str
    venture_id: str
    status: ApprovalStatus
    final_price: Optional[float]
    message: str
