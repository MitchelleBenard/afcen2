from sqlalchemy import Column, String, Integer, Float, DateTime, Enum, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime, timezone
import uuid
import enum


def generate_id():
    return str(uuid.uuid4())

def now_utc():
    return datetime.now(timezone.utc)


# --- Enums ---

class VentureStatus(str, enum.Enum):
    DRAFT = "draft"        # Just created from intake
    ACTIVE = "active"      # Builder approved and it's live
    PAUSED = "paused"      # Builder paused it


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"      # Agent proposed, waiting for builder
    APPROVED = "approved"    # Builder said yes
    REJECTED = "rejected"    # Builder said no
    EDITED = "edited"        # Builder changed the value then approved


class IntentType(str, enum.Enum):
    PRODUCER_TO_MARKET = "producer_to_market"  # Farmer selling direct
    AGGREGATION = "aggregation"                # Trader buying from many
    LOCAL_SERVICE = "local_service"            # Repair, delivery, etc
    ADVISORY = "advisory"                      # Just wants advice


# --- Tables ---

class Builder(Base):
    """The person using the platform — Ama, Kwesi, etc."""
    __tablename__ = "builders"

    id = Column(String, primary_key=True, default=generate_id)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    ventures = relationship("Venture", back_populates="builder")


class Venture(Base):
    """One business a builder is running. The core object everything hangs off."""
    __tablename__ = "ventures"

    id = Column(String, primary_key=True, default=generate_id)
    builder_id = Column(String, ForeignKey("builders.id"), nullable=False)

    raw_message = Column(Text, nullable=False)       # What the builder typed
    intent = Column(Enum(IntentType), nullable=False) # What the AI understood
    commodity = Column(String, nullable=True)         # e.g. "tomato"
    location = Column(String, nullable=True)          # e.g. "tamale"
    quantity = Column(Integer, nullable=True)         # e.g. 80
    quantity_unit = Column(String, nullable=True)     # e.g. "crates"

    status = Column(Enum(VentureStatus), default=VentureStatus.DRAFT)
    created_at = Column(DateTime(timezone=True), default=now_utc)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    builder = relationship("Builder", back_populates="ventures")
    offers = relationship("Offer", back_populates="venture")
    approvals = relationship("Approval", back_populates="venture")


class Offer(Base):
    """What the venture is selling. Price is empty until agent proposes and builder approves."""
    __tablename__ = "offers"

    id = Column(String, primary_key=True, default=generate_id)
    venture_id = Column(String, ForeignKey("ventures.id"), nullable=False)

    commodity = Column(String, nullable=False)
    quantity = Column(Integer, nullable=True)
    quantity_unit = Column(String, nullable=True)
    currency = Column(String, default="GHS")

    price_low = Column(Float, nullable=True)    # Agent's suggested low
    price_high = Column(Float, nullable=True)   # Agent's suggested high
    price_set = Column(Float, nullable=True)    # Final approved price

    created_at = Column(DateTime(timezone=True), default=now_utc)

    venture = relationship("Venture", back_populates="offers")


class Approval(Base):
    """
    Every important agent action creates an Approval record first.
    Nothing changes in the real world until builder approves.
    """
    __tablename__ = "approvals"

    id = Column(String, primary_key=True, default=generate_id)
    venture_id = Column(String, ForeignKey("ventures.id"), nullable=False)

    action_type = Column(String, nullable=False)    # e.g. "set_price"
    proposed_value = Column(Text, nullable=True)    # JSON: what the agent wants to do
    agent_reasoning = Column(Text, nullable=True)   # Plain English explanation

    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    builder_value = Column(Text, nullable=True)     # Builder's edit if they changed it

    created_at = Column(DateTime(timezone=True), default=now_utc)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    venture = relationship("Venture", back_populates="approvals")
