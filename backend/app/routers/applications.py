from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app import models, schemas
from app.database import get_db
from app.security import get_current_user, require_role

router = APIRouter(prefix="/applications", tags=["applications"])


def _enrich_app(app: models.LoanApplication, db: Session) -> models.LoanApplication:
    user = db.query(models.User).filter(models.User.id == app.user_id).first()
    scheme = db.query(models.Scheme).filter(models.Scheme.id == app.scheme_id).first()
    partner = db.query(models.ChannelPartner).filter(models.ChannelPartner.id == app.partner_id).first()
    app.applicant_name = user.name if user else "Beneficiary"
    app.scheme_name = scheme.name if scheme else "NSFDC Scheme"
    app.partner_name = partner.name if partner else "Channel Partner"
    return app


@router.get("/", response_model=List[schemas.LoanApplicationRead])
def list_applications(
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(models.LoanApplication)

    # RBAC: Citizens can only see their own applications
    if current_user.role == "citizen":
        q = q.filter(models.LoanApplication.user_id == current_user.id)
    elif user_id:
        q = q.filter(models.LoanApplication.user_id == user_id)

    if status:
        q = q.filter(models.LoanApplication.status == status)

    apps = q.order_by(models.LoanApplication.created_at.desc()).offset(skip).limit(limit).all()
    for a in apps:
        _enrich_app(a, db)
    return apps


@router.get("/{application_id}", response_model=schemas.LoanApplicationRead)
def get_application(
    application_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    app = db.query(models.LoanApplication).filter(models.LoanApplication.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Loan application not found")

    # RBAC: Citizen cannot view another user's application
    if current_user.role == "citizen" and app.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to view this application.",
        )

    _enrich_app(app, db)
    return app


@router.post("/", response_model=schemas.LoanApplicationRead, status_code=201)
def create_application(
    payload: schemas.LoanApplicationCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    import uuid
    from datetime import datetime

    # If citizen, force application to belong to current_user
    target_user_id = current_user.id if current_user.role == "citizen" else payload.user_id

    # Validate referenced entities exist
    if not db.query(models.User).filter(models.User.id == target_user_id).first():
        raise HTTPException(status_code=404, detail="User not found")
    if not db.query(models.Scheme).filter(models.Scheme.id == payload.scheme_id).first():
        raise HTTPException(status_code=404, detail="Scheme not found")
    if not db.query(models.ChannelPartner).filter(models.ChannelPartner.id == payload.partner_id).first():
        raise HTTPException(status_code=404, detail="Channel partner not found")

    data = payload.model_dump()
    data["user_id"] = target_user_id

    db_app = models.LoanApplication(
        id=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        **data,
    )
    db.add(db_app)
    db.commit()
    db.refresh(db_app)
    _enrich_app(db_app, db)
    return db_app


@router.patch("/{application_id}/status", response_model=schemas.LoanApplicationRead)
def update_application_status(
    application_id: str,
    status: str,
    current_admin: models.User = Depends(require_role("bank_admin")),
    db: Session = Depends(get_db),
):
    valid_statuses = {"Pending", "Under_Review", "Approved", "Disbursed", "Rejected"}
    if status not in valid_statuses:
        raise HTTPException(status_code=422, detail=f"status must be one of {valid_statuses}")

    app = db.query(models.LoanApplication).filter(models.LoanApplication.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Loan application not found")

    app.status = status
    db.commit()
    db.refresh(app)
    _enrich_app(app, db)
    return app


@router.delete("/{application_id}", status_code=204)
def delete_application(
    application_id: str,
    current_admin: models.User = Depends(require_role("bank_admin")),
    db: Session = Depends(get_db),
):
    app = db.query(models.LoanApplication).filter(models.LoanApplication.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Loan application not found")
    db.delete(app)
    db.commit()
