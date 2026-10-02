from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from geoalchemy2.shape import to_shape
from geoalchemy2.elements import WKTElement

from app import models, schemas
from app.database import get_db
from app.security import get_current_user, require_role

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=List[schemas.UserRead])
def list_users(
    skip: int = 0,
    limit: int = 100,
    current_admin: models.User = Depends(require_role("bank_admin")),
    db: Session = Depends(get_db),
):
    """Admin-only: List all registered beneficiaries."""
    users = db.query(models.User).filter(models.User.role == "citizen").offset(skip).limit(limit).all()
    for u in users:
        # Clean display domain if internal email placeholder was used
        if u.project_domain and u.project_domain.startswith("__email__"):
            u.project_domain = "Self-Employment / Beneficiary"
        if u.location is not None:
            shape = to_shape(u.location)
            u.lat = shape.y
            u.lng = shape.x
    return users


@router.get("/{user_id}", response_model=schemas.UserRead)
def get_user(
    user_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user profile: allowed for the user themselves or bank admins."""
    if current_user.role == "citizen" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You can only view your own user profile.",
        )

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.project_domain and user.project_domain.startswith("__email__"):
        user.project_domain = "Self-Employment / Beneficiary"
    if user.location is not None:
        shape = to_shape(user.location)
        user.lat = shape.y
        user.lng = shape.x
    return user


@router.post("/", response_model=schemas.UserRead, status_code=201)
def create_user(
    payload: schemas.UserCreate,
    current_admin: models.User = Depends(require_role("bank_admin")),
    db: Session = Depends(get_db),
):
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
def update_user(
    user_id: str,
    payload: schemas.UserCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == "citizen" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You can only update your own user profile.",
        )

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
def delete_user(
    user_id: str,
    current_admin: models.User = Depends(require_role("bank_admin")),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
