from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/schemes", tags=["schemes"])


@router.get("/", response_model=List[schemas.SchemeRead])
def list_schemes(db: Session = Depends(get_db)):
    return db.query(models.Scheme).all()


@router.get("/{scheme_id}", response_model=schemas.SchemeRead)
def get_scheme(scheme_id: str, db: Session = Depends(get_db)):
    scheme = db.query(models.Scheme).filter(models.Scheme.id == scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    return scheme


@router.post("/", response_model=schemas.SchemeRead, status_code=201)
def create_scheme(payload: schemas.SchemeCreate, db: Session = Depends(get_db)):
    import uuid
    db_scheme = models.Scheme(id=str(uuid.uuid4()), **payload.model_dump())
    db.add(db_scheme)
    db.commit()
    db.refresh(db_scheme)
    return db_scheme


@router.put("/{scheme_id}", response_model=schemas.SchemeRead)
def update_scheme(scheme_id: str, payload: schemas.SchemeCreate, db: Session = Depends(get_db)):
    scheme = db.query(models.Scheme).filter(models.Scheme.id == scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    for key, value in payload.model_dump().items():
        setattr(scheme, key, value)
    db.commit()
    db.refresh(scheme)
    return scheme


@router.delete("/{scheme_id}", status_code=204)
def delete_scheme(scheme_id: str, db: Session = Depends(get_db)):
    scheme = db.query(models.Scheme).filter(models.Scheme.id == scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    db.delete(scheme)
    db.commit()
