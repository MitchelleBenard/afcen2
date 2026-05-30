from pydantic import BaseModel, Field
from typing import Optional
from app.models import VentureStatus, IntentType


class IntakeRequest(BaseModel):
    builder_id: str = Field(..., description="The builder's unique ID")
    message: str = Field(..., description="Plain language message from the builder")

    model_config = {"json_schema_extra": {
        "example": {
            "builder_id": "builder-001",
            "message": "I have 80 crates of tomatoes in Tamale, what should I charge?"
        }
    }}


class IntakeResponse(BaseModel):
    venture_id: str
    intent: IntentType
    commodity: Optional[str]
    location: Optional[str]
    quantity: Optional[int]
    quantity_unit: Optional[str]
    status: VentureStatus
    message: str  # Plain English summary of what the AI understood
