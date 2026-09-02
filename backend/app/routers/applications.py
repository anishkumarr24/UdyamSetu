from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("/", response_model=List[schemas.LoanApplicationRead])
def list_applications(
    user_id: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    q = db.query(models.LoanApplication)
    if user_id:
        q = q.filter(models.LoanApplication.user_id == user_id)
    if status:
        q = q.filter(models.LoanApplication.status == status)
    return q.offset(skip).limit(limit).all()


@router.get("/{application_id}", response_model=schemas.LoanApplicationRead)
def get_application(application_id: str, db: Session = Depends(get_db)):
    app = db.query(models.LoanApplication).filter(models.LoanApplication.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Loan application not found")
    return app


@router.post("/", response_model=schemas.LoanApplicationRead, status_code=201)
def create_application(payload: schemas.LoanApplicationCreate, db: Session = Depends(get_db)):
    import uuid
    from datetime import datetime

    # Validate referenced entities exist
    if not db.query(models.User).filter(models.User.id == payload.user_id).first():
        raise HTTPException(status_code=404, detail="User not found")
    if not db.query(models.Scheme).filter(models.Scheme.id == payload.scheme_id).first():
        raise HTTPException(status_code=404, detail="Scheme not found")
    if not db.query(models.ChannelPartner).filter(models.ChannelPartner.id == payload.partner_id).first():
        raise HTTPException(status_code=404, detail="Channel partner not found")

    db_app = models.LoanApplication(
        id=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        **payload.model_dump(),
    )
    db.add(db_app)
    db.commit()
    db.refresh(db_app)
    return db_app


@router.patch("/{application_id}/status", response_model=schemas.LoanApplicationRead)
def update_application_status(
    application_id: str,
    status: str,
    db: Session = Depends(get_db),
):
    valid_statuses = {"Pending", "Under_Review", "Approved", "Disbursed"}
    if status not in valid_statuses:
        raise HTTPException(status_code=422, detail=f"status must be one of {valid_statuses}")
    app = db.query(models.LoanApplication).filter(models.LoanApplication.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Loan application not found")
    app.status = status
    db.commit()
    db.refresh(app)
    return app


@router.delete("/{application_id}", status_code=204)
def delete_application(application_id: str, db: Session = Depends(get_db)):
    app = db.query(models.LoanApplication).filter(models.LoanApplication.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Loan application not found")
    db.delete(app)
    db.commit()
