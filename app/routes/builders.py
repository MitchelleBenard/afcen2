from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from app.models import Builder, Venture
from app.schemas import BuilderCreate, BuilderResponse, VentureResponse

router = APIRouter(prefix="/builders", tags=["Builders"])


@router.get("/", response_model=List[BuilderResponse])
def list_builders(db: Session = Depends(get_db)):
    """List all builders — used by the UI to populate the dropdown."""
    return db.query(Builder).order_by(Builder.created_at).all()


@router.post("/", response_model=BuilderResponse, status_code=201)
def create_builder(payload: BuilderCreate, db: Session = Depends(get_db)):
    """Register a new builder."""
    builder = Builder(name=payload.name)
    db.add(builder)
    db.commit()
    db.refresh(builder)
    return builder


@router.get("/{builder_id}", response_model=BuilderResponse)
def get_builder(builder_id: str, db: Session = Depends(get_db)):
    builder = db.query(Builder).filter(Builder.id == builder_id).first()
    if not builder:
        raise HTTPException(status_code=404, detail="Builder not found")
    return builder


@router.get("/{builder_id}/ventures", response_model=List[VentureResponse])
def list_builder_ventures(builder_id: str, db: Session = Depends(get_db)):
    """List all ventures for a builder — used by the UI sidebar."""
    builder = db.query(Builder).filter(Builder.id == builder_id).first()
    if not builder:
        raise HTTPException(status_code=404, detail="Builder not found")
    return db.query(Venture).filter(Venture.builder_id == builder_id).order_by(Venture.created_at.desc()).all()
