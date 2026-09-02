"""
security.py – JWT-based authentication utilities.

Provides:
  - create_access_token(data, expires_delta) → signed JWT string
  - get_current_user(token)                  → FastAPI dependency → User ORM obj
  - require_role(role)                        → FastAPI dependency factory → User ORM obj
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.database import get_db
from app import models

# ── Config (mirrors .env values loaded by pydantic-settings in config.py) ─────
import os

SECRET_KEY = os.getenv("K8xQ2mLp9VzR4wY7tN6cA1sF5jH3dE8uB0gX9pL2rT6kM")
ALGORITHM  = "HS256"
TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ── Token helpers ──────────────────────────────────────────────────────────────

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    payload = data.copy()
    expire  = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    )
    payload["exp"] = expire
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ── Dependencies ───────────────────────────────────────────────────────────────

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exc
    return user


def require_role(role: str):
    """
    Dependency factory.  Usage:
        @router.get("/...", dependencies=[Depends(require_role("bank_admin"))])
    or as a typed dependency:
        user: User = Depends(require_role("bank_admin"))
    """
    def _check(current_user: models.User = Depends(get_current_user)) -> models.User:
        if current_user.role != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access restricted to '{role}' role.",
            )
        return current_user
    return _check
