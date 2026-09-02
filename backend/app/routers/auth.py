"""
auth.py – Registration and login endpoints.

Routes:
  POST /api/v1/auth/register  – Create a new citizen or bank_admin account.
  POST /api/v1/auth/login     – OAuth2 password flow → JWT bearer token.
  GET  /api/v1/auth/me        – Return the current authenticated user profile.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
import bcrypt
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session
from typing import Literal, Optional

from app import models
from app.database import get_db
from app.security import create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

# ── Schemas ────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    email: str                       # used as login username
    password: str
    role: Literal["citizen", "bank_admin"] = "citizen"
    # Optional profile fields (can be filled later on /apply)
    age: Optional[int]              = None
    gender: Optional[str]           = None
    category: Optional[str]         = None
    annual_income: Optional[float]  = None
    project_domain: Optional[str]   = None
    requested_amount: Optional[float] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters.")
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    name: str
    role: str


class UserProfileResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    age: Optional[int]
    gender: Optional[str]
    category: Optional[str]
    annual_income: Optional[float]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _hash(pw: str) -> str:
    salt = bcrypt.gensalt()
    # bcrypt expects bytes
    hashed = bcrypt.hashpw(pw.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def _verify(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except ValueError:
        return False


def _get_by_email(db: Session, email: str) -> Optional[models.User]:
    # We store email in the `name` field for auth-only accounts, but to avoid
    # collisions we use `project_domain` as an email slot for registered users.
    # A cleaner approach would be a dedicated email column — we simulate that
    # by encoding it into `project_domain` with a sentinel prefix.
    return (
        db.query(models.User)
          .filter(models.User.project_domain == f"__email__{email}")
          .first()
    )


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201,
             summary="Register a new citizen or bank_admin account")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if _get_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists.",
        )

    user = models.User(
        id               = str(uuid.uuid4()),
        name             = payload.name,
        age              = payload.age or 0,
        gender           = payload.gender or "Other",
        category         = payload.category or "General",
        annual_income    = payload.annual_income or 0.0,
        project_domain   = f"__email__{payload.email}",
        requested_amount = payload.requested_amount or 0.0,
        readiness_score  = 0.0,
        hashed_password  = _hash(payload.password),
        role             = payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.id, "role": user.role})
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        name=user.name,
        role=user.role,
    )


@router.post("/login", response_model=TokenResponse,
             summary="Login and receive a JWT bearer token")
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db:   Session                   = Depends(get_db),
):
    user = _get_by_email(db, form.username)
    if not user or not user.hashed_password or not _verify(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": user.id, "role": user.role})
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        name=user.name,
        role=user.role,
    )


@router.get("/me", response_model=UserProfileResponse,
            summary="Return the current user's profile")
def me(current_user: models.User = Depends(get_current_user)):
    email = ""
    if current_user.project_domain and current_user.project_domain.startswith("__email__"):
        email = current_user.project_domain[len("__email__"):]
    return UserProfileResponse(
        id            = current_user.id,
        name          = current_user.name,
        email         = email,
        role          = current_user.role,
        age           = current_user.age or None,
        gender        = current_user.gender or None,
        category      = current_user.category or None,
        annual_income = current_user.annual_income or None,
    )
