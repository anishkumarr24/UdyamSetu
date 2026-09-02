from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


# ── User ─────────────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    name: str
    age: int
    gender: str
    category: str
    annual_income: float
    project_domain: str
    requested_amount: float
    lat: Optional[float] = None
    lng: Optional[float] = None
    readiness_score: float = 0.0
    has_udyam: bool = False
    has_caste_cert: bool = False
    has_income_cert: bool = False


class UserCreate(UserBase):
    pass


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: str


# ── Scheme ────────────────────────────────────────────────────────────────────

class SchemeBase(BaseModel):
    name: str
    min_amount: float = 0.0
    max_amount: float
    max_income: float
    base_interest_rate: float
    min_moratorium_months: int
    max_moratorium_months: int
    required_category: str
    description: str = ""


class SchemeCreate(SchemeBase):
    pass


class SchemeRead(SchemeBase):
    model_config = ConfigDict(from_attributes=True)
    id: str


# ── ChannelPartner ────────────────────────────────────────────────────────────

class ChannelPartnerBase(BaseModel):
    name: str
    partner_type: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    npa_percentage: float = 0.0
    is_active: bool = True
    contact_phone: str = ""
    contact_email: str = ""


class ChannelPartnerCreate(ChannelPartnerBase):
    pass


class ChannelPartnerRead(ChannelPartnerBase):
    model_config = ConfigDict(from_attributes=True)
    id: str


# ── LoanApplication ───────────────────────────────────────────────────────────

class LoanApplicationBase(BaseModel):
    user_id: str
    scheme_id: str
    partner_id: str
    amount: float
    tenure_months: int
    moratorium_months: int
    status: str = "Pending"


class LoanApplicationCreate(LoanApplicationBase):
    pass


class LoanApplicationRead(LoanApplicationBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
