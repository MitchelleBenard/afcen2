from pydantic import BaseModel
from datetime import datetime
from app.models import VentureStatus, IntentType
from typing import Optional


class VentureResponse(BaseModel):
    id: str
    builder_id: str
    raw_message: str
    intent: IntentType
    commodity: Optional[str]
    location: Optional[str]
    quantity: Optional[int]
    quantity_unit: Optional[str]
    status: VentureStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class BuilderCreate(BaseModel):
    name: str

    model_config = {"json_schema_extra": {"example": {"name": "Ama Asante"}}}


class BuilderResponse(BaseModel):
    id: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}
