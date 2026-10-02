from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from geoalchemy2.shape import to_shape
from geoalchemy2.elements import WKTElement

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=List[schemas.UserRead])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = db.query(models.User).offset(skip).limit(limit).all()
    for u in users:
        if u.location is not None:
            shape = to_shape(u.location)
            u.lat = shape.y
            u.lng = shape.x
    return users


@router.get("/{user_id}", response_model=schemas.UserRead)
def get_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.location is not None:
        shape = to_shape(user.location)
        user.lat = shape.y
        user.lng = shape.x
    return user


@router.post("/", response_model=schemas.UserRead, status_code=201)
def create_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    import uuid
    data = payload.model_dump()
    lat = data.pop("lat", None)
    lng = data.pop("lng", None)
    location = None
    if lat is not None and lng is not None:
        location = WKTElement(f"POINT({lng} {lat})", srid=4326)
    db_user = models.User(id=str(uuid.uuid4()), location=location, **data)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    db_user.lat = lat
    db_user.lng = lng
    return db_user


@router.put("/{user_id}", response_model=schemas.UserRead)
def update_user(user_id: str, payload: schemas.UserCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    data = payload.model_dump()
    lat = data.pop("lat", None)
    lng = data.pop("lng", None)
    if lat is not None and lng is not None:
        user.location = WKTElement(f"POINT({lng} {lat})", srid=4326)
    for key, value in data.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    if user.location is not None:
        shape = to_shape(user.location)
        user.lat = shape.y
        user.lng = shape.x
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
