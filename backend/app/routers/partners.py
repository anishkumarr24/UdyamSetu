from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from geoalchemy2.shape import to_shape
from geoalchemy2.elements import WKTElement

from app import models, schemas
from app.database import get_db
from app.security import require_role

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


@router.post("/", response_model=schemas.ChannelPartnerRead, status_code=201,
             dependencies=[Depends(require_role("bank_admin"))])
def create_partner(payload: schemas.ChannelPartnerCreate, db: Session = Depends(get_db)):
    import uuid
    data = payload.model_dump()
    lat = data.pop("lat", None)
    lng = data.pop("lng", None)
    location = None
    if lat is not None and lng is not None:
        location = WKTElement(f"POINT({lng} {lat})", srid=4326)
    db_partner = models.ChannelPartner(id=str(uuid.uuid4()), location=location, **data)
    db.add(db_partner)
    db.commit()
    db.refresh(db_partner)
    db_partner.lat = lat
    db_partner.lng = lng
    return db_partner


@router.put("/{partner_id}", response_model=schemas.ChannelPartnerRead,
            dependencies=[Depends(require_role("bank_admin"))])
def update_partner(partner_id: str, payload: schemas.ChannelPartnerCreate, db: Session = Depends(get_db)):
    partner = db.query(models.ChannelPartner).filter(models.ChannelPartner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Channel partner not found")
    data = payload.model_dump()
    lat = data.pop("lat", None)
    lng = data.pop("lng", None)
    if lat is not None and lng is not None:
        partner.location = WKTElement(f"POINT({lng} {lat})", srid=4326)
    for key, value in data.items():
        setattr(partner, key, value)
    db.commit()
    db.refresh(partner)
    if partner.location is not None:
        shape = to_shape(partner.location)
        partner.lat = shape.y
        partner.lng = shape.x
    return partner


@router.delete("/{partner_id}", status_code=204,
               dependencies=[Depends(require_role("bank_admin"))])
def delete_partner(partner_id: str, db: Session = Depends(get_db)):
    partner = db.query(models.ChannelPartner).filter(models.ChannelPartner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Channel partner not found")
    db.delete(partner)
    db.commit()
