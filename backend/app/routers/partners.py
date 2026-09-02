from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from geoalchemy2.shape import to_shape

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/partners", tags=["partners"])


@router.get("/", response_model=List[schemas.ChannelPartnerRead])
def list_partners(active_only: bool = False, db: Session = Depends(get_db)):
    q = db.query(models.ChannelPartner)
    if active_only:
        q = q.filter(models.ChannelPartner.is_active == True)
    partners = q.all()
    for p in partners:
        if p.location is not None:
            shape = to_shape(p.location)
            p.lat = shape.y
            p.lng = shape.x
    return partners


@router.get("/{partner_id}", response_model=schemas.ChannelPartnerRead)
def get_partner(partner_id: str, db: Session = Depends(get_db)):
    partner = db.query(models.ChannelPartner).filter(models.ChannelPartner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Channel partner not found")
    if partner.location is not None:
        shape = to_shape(partner.location)
        partner.lat = shape.y
        partner.lng = shape.x
    return partner


@router.post("/", response_model=schemas.ChannelPartnerRead, status_code=201)
def create_partner(payload: schemas.ChannelPartnerCreate, db: Session = Depends(get_db)):
    import uuid
    db_partner = models.ChannelPartner(id=str(uuid.uuid4()), **payload.model_dump())
    db.add(db_partner)
    db.commit()
    db.refresh(db_partner)
    return db_partner


@router.put("/{partner_id}", response_model=schemas.ChannelPartnerRead)
def update_partner(partner_id: str, payload: schemas.ChannelPartnerCreate, db: Session = Depends(get_db)):
    partner = db.query(models.ChannelPartner).filter(models.ChannelPartner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Channel partner not found")
    for key, value in payload.model_dump().items():
        setattr(partner, key, value)
    db.commit()
    db.refresh(partner)
    return partner


@router.delete("/{partner_id}", status_code=204)
def delete_partner(partner_id: str, db: Session = Depends(get_db)):
    partner = db.query(models.ChannelPartner).filter(models.ChannelPartner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Channel partner not found")
    db.delete(partner)
    db.commit()
