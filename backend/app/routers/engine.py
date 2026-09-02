"""
engine.py – Core algorithmic endpoints for UdyamSetu.
Routes:
  POST /api/match-scheme           – eligibility + ML-powered readiness scoring + gap analysis
  POST /api/calculate-emi          – moratorium-aware EMI schedule
  POST /api/find-partners          – PostGIS-filtered healthy channel partners
  GET  /api/admin/applications     – mocked submitted applications list
  POST /api/admin/simulate-npa     – update a partner's NPA in the DB (demo control)
"""

from typing import Optional, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.ml_loader import get_readiness_score, MODEL_READY
from app.security import require_role

router = APIRouter(prefix="/api", tags=["engine"])

# ────────────────────────────────────────────────────────────────────────────
# Schemas
# ────────────────────────────────────────────────────────────────────────────

class MatchSchemeRequest(BaseModel):
    user_id: Optional[str] = None
    name: str
    age: int
    gender: str
    category: str
    annual_income: float
    project_domain: str
    requested_amount: float
    has_udyam: bool = False
    has_caste_cert: bool = False
    has_income_cert: bool = False


class SchemeSnapshot(BaseModel):
    id: str
    name: str
    max_amount: float
    max_income: float
    base_interest_rate: float
    min_moratorium_months: int
    max_moratorium_months: int
    required_category: str
    description: str


class MatchSchemeResponse(BaseModel):
    is_eligible: bool
    ineligibility_reason: Optional[str] = None
    matched_scheme: Optional[SchemeSnapshot] = None
    readiness_score: int
    gaps: List[str]
    subsidy_amount: float


# ── EMI ──────────────────────────────────────────────────────────────────────

class EMIRequest(BaseModel):
    principal: float = Field(..., gt=0)
    annual_interest_rate: float = Field(..., gt=0)
    tenure_months: int = Field(..., gt=0)
    moratorium_months: int = Field(..., ge=0)


class EMIScheduleRow(BaseModel):
    month: int
    principal_paid: float
    interest_paid: float
    remaining_balance: float


class EMIResponse(BaseModel):
    moratorium_monthly_payment: float
    regular_emi: float
    total_interest_paid: float
    total_amount_payable: float
    schedule: List[EMIScheduleRow]


# ── Find Partners ─────────────────────────────────────────────────────────────

class FindPartnersRequest(BaseModel):
    user_lat: float
    user_lng: float
    radius_km: float = 50.0


class PartnerResult(BaseModel):
    id: str
    name: str
    partner_type: str
    lat: float
    lng: float
    npa_percentage: float
    is_active: bool
    contact_phone: str
    contact_email: str
    distance_km: float

    model_config = {"from_attributes": True}


class FindPartnersResponse(BaseModel):
    partners: List[PartnerResult]
    total_found: int


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

def _round2(x: float) -> float:
    return round(x, 2)


# ────────────────────────────────────────────────────────────────────────────
# POST /api/match-scheme
# ────────────────────────────────────────────────────────────────────────────

@router.post("/match-scheme", response_model=MatchSchemeResponse, summary="Match eligible NSFDC scheme")
def match_scheme(req: MatchSchemeRequest, db: Session = Depends(get_db)):
    # ── 1. Hard eligibility filter ────────────────────────────────────────────
    if req.category != "SC":
        return MatchSchemeResponse(
            is_eligible=False,
            ineligibility_reason=(
                f"Category '{req.category}' is not eligible. "
                "NSFDC schemes under this portal are restricted to SC beneficiaries."
            ),
            readiness_score=0,
            gaps=["Category must be SC"],
            subsidy_amount=0.0,
        )

    if req.annual_income > 300_000:
        return MatchSchemeResponse(
            is_eligible=False,
            ineligibility_reason=(
                f"Annual income ₹{req.annual_income:,.0f} exceeds the maximum limit of "
                "₹3,00,000 for NSFDC financial assistance."
            ),
            readiness_score=0,
            gaps=["Annual income exceeds ₹3,00,000 ceiling"],
            subsidy_amount=0.0,
        )

    # ── 2. Scheme selection ───────────────────────────────────────────────────
    domain_lower = req.project_domain.lower()
    is_education = any(k in domain_lower for k in ("education", "higher stud", "study", "studies"))

    if is_education:
        scheme_name = "NSFDC Education Loan"
    elif req.requested_amount <= 140_000:
        scheme_name = "NSFDC Micro Finance"
    else:
        scheme_name = "NSFDC Term Loan"

    scheme_obj = db.query(models.Scheme).filter(models.Scheme.name == scheme_name).first()

    # Fallback: if scheme not yet seeded return first scheme
    if scheme_obj is None:
        scheme_obj = db.query(models.Scheme).first()

    matched: Optional[SchemeSnapshot] = None
    if scheme_obj:
        matched = SchemeSnapshot(
            id=scheme_obj.id,
            name=scheme_obj.name,
            max_amount=scheme_obj.max_amount,
            max_income=scheme_obj.max_income,
            base_interest_rate=scheme_obj.base_interest_rate,
            min_moratorium_months=scheme_obj.min_moratorium_months,
            max_moratorium_months=scheme_obj.max_moratorium_months,
            required_category=scheme_obj.required_category,
            description=scheme_obj.description,
        )

    # ── 3. ML readiness score + dynamic gap analysis ─────────────────────────
    # Fetch the healthiest active partner's NPA to factor into the model.
    # If no partners exist yet, use a neutral 5.0%.
    best_partner = (
        db.query(models.ChannelPartner)
        .filter(models.ChannelPartner.is_active == True)  # noqa: E712
        .order_by(models.ChannelPartner.npa_percentage.asc())
        .first()
    )
    partner_npa = best_partner.npa_percentage if best_partner else 5.0

    score, gaps = get_readiness_score(
        age=req.age,
        annual_income=req.annual_income,
        requested_amount=req.requested_amount,
        has_udyam=req.has_udyam,
        has_caste_cert=req.has_caste_cert,
        has_income_cert=req.has_income_cert,
        partner_npa=partner_npa,
        category=req.category,
    )

    # ── 4. Subsidy calculation ────────────────────────────────────────────────
    # 20% of loan amount, capped at ₹50,000
    loan_amount = min(req.requested_amount, scheme_obj.max_amount if scheme_obj else req.requested_amount)
    subsidy_amount = min(loan_amount * 0.20, 50_000.0)

    # Persist readiness score back to user row (if user_id provided)
    if req.user_id:
        user_row = db.query(models.User).filter(models.User.id == req.user_id).first()
        if user_row:
            user_row.readiness_score = float(score)
            db.commit()

    return MatchSchemeResponse(
        is_eligible=True,
        matched_scheme=matched,
        readiness_score=score,
        gaps=gaps,
        subsidy_amount=_round2(subsidy_amount),
    )


# ────────────────────────────────────────────────────────────────────────────
# POST /api/calculate-emi
# ────────────────────────────────────────────────────────────────────────────

@router.post("/calculate-emi", response_model=EMIResponse, summary="Moratorium-aware EMI schedule")
def calculate_emi(req: EMIRequest):
    P = req.principal
    r_annual = req.annual_interest_rate
    n = req.tenure_months
    m = req.moratorium_months

    monthly_rate = (r_annual / 100) / 12

    # ── Moratorium phase: simple interest only ────────────────────────────────
    moratorium_payment = _round2(P * monthly_rate)

    # ── EMI phase: reducing-balance over remaining months ─────────────────────
    remaining_months = n - m
    if remaining_months <= 0:
        # Entire tenure is moratorium — edge case
        regular_emi = moratorium_payment
        remaining_months = 0
    elif monthly_rate == 0:
        regular_emi = _round2(P / remaining_months)
    else:
        # Standard EMI formula: P * r * (1+r)^n / ((1+r)^n - 1)
        factor = (1 + monthly_rate) ** remaining_months
        regular_emi = _round2(P * monthly_rate * factor / (factor - 1))

    # ── Build full schedule ───────────────────────────────────────────────────
    schedule: List[EMIScheduleRow] = []
    balance = P
    total_interest = 0.0
    total_paid = 0.0

    # Moratorium months
    for month in range(1, m + 1):
        interest = _round2(balance * monthly_rate)
        total_interest += interest
        total_paid += interest
        schedule.append(EMIScheduleRow(
            month=month,
            principal_paid=0.0,
            interest_paid=interest,
            remaining_balance=_round2(balance),
        ))

    # EMI months
    for month in range(m + 1, n + 1):
        if balance <= 0:
            break
        interest = _round2(balance * monthly_rate)
        principal_paid = _round2(regular_emi - interest)
        # Last month adjustment to clear balance
        if month == n or principal_paid >= balance:
            principal_paid = _round2(balance)
            emi_this_month = _round2(principal_paid + interest)
        else:
            emi_this_month = regular_emi
        balance = _round2(max(0.0, balance - principal_paid))
        total_interest += interest
        total_paid += emi_this_month
        schedule.append(EMIScheduleRow(
            month=month,
            principal_paid=principal_paid,
            interest_paid=interest,
            remaining_balance=balance,
        ))

    return EMIResponse(
        moratorium_monthly_payment=moratorium_payment,
        regular_emi=regular_emi,
        total_interest_paid=_round2(total_interest),
        total_amount_payable=_round2(total_paid),
        schedule=schedule,
    )


# ────────────────────────────────────────────────────────────────────────────
# POST /api/find-partners
# ────────────────────────────────────────────────────────────────────────────

@router.post("/find-partners", response_model=FindPartnersResponse, summary="Nearby healthy channel partners")
def find_partners(req: FindPartnersRequest, db: Session = Depends(get_db)):
    from sqlalchemy import text

    radius_m = req.radius_km * 1000.0

    # Native PostGIS query: filter active/healthy partners within radius,
    # compute distance via ST_DistanceSphere, sort ascending.
    sql = text("""
        SELECT
            id,
            name,
            partner_type,
            ST_Y(location::geometry)          AS lat,
            ST_X(location::geometry)          AS lng,
            npa_percentage,
            is_active,
            contact_phone,
            contact_email,
            ST_DistanceSphere(
                location::geometry,
                ST_SetSRID(ST_MakePoint(:user_lng, :user_lat), 4326)
            ) / 1000.0                        AS distance_km
        FROM channel_partners
        WHERE is_active = TRUE
          AND npa_percentage <= 8.0
          AND ST_DistanceSphere(
                location::geometry,
                ST_SetSRID(ST_MakePoint(:user_lng, :user_lat), 4326)
              ) <= :radius_m
        ORDER BY distance_km ASC
    """)

    rows = db.execute(
        sql,
        {"user_lat": req.user_lat, "user_lng": req.user_lng, "radius_m": radius_m},
    ).mappings().all()

    results = [
        PartnerResult(
            id=row["id"],
            name=row["name"],
            partner_type=row["partner_type"],
            lat=row["lat"],
            lng=row["lng"],
            npa_percentage=row["npa_percentage"],
            is_active=row["is_active"],
            contact_phone=row["contact_phone"],
            contact_email=row["contact_email"],
            distance_km=_round2(row["distance_km"]),
        )
        for row in rows
    ]

    return FindPartnersResponse(partners=results, total_found=len(results))


# ────────────────────────────────────────────────────────────────────────────
# GET /api/admin/applications
# ────────────────────────────────────────────────────────────────────────────

class AdminApplication(BaseModel):
    id: str
    applicant_name: str
    domain: str
    requested_amount: float
    matched_scheme: str
    readiness_score: int
    status: str
    submitted_on: str
    category: str
    annual_income: float


MOCK_ADMIN_APPLICATIONS = [
    AdminApplication(id="APP-001", applicant_name="Rajesh Kumar",    domain="Tailoring",          requested_amount=50000,   matched_scheme="NSFDC Micro Finance",   readiness_score=80,  status="Under Review", submitted_on="2024-08-01", category="SC", annual_income=180000),
    AdminApplication(id="APP-002", applicant_name="Sunita Devi",     domain="Food Processing",    requested_amount=120000,  matched_scheme="NSFDC Micro Finance",   readiness_score=100, status="Sanctioned",   submitted_on="2024-08-03", category="SC", annual_income=220000),
    AdminApplication(id="APP-003", applicant_name="Mohan Das",       domain="Animal Husbandry",   requested_amount=350000,  matched_scheme="NSFDC Term Loan",       readiness_score=60,  status="Pending",      submitted_on="2024-08-05", category="SC", annual_income=250000),
    AdminApplication(id="APP-004", applicant_name="Priya Mondal",    domain="Higher Studies",     requested_amount=800000,  matched_scheme="NSFDC Education Loan",  readiness_score=70,  status="Under Review", submitted_on="2024-08-07", category="SC", annual_income=160000),
    AdminApplication(id="APP-005", applicant_name="Arjun Haldar",    domain="Small Manufacturing",requested_amount=2500000, matched_scheme="NSFDC Term Loan",       readiness_score=90,  status="Sanctioned",   submitted_on="2024-08-09", category="SC", annual_income=280000),
    AdminApplication(id="APP-006", applicant_name="Kavita Sarkar",   domain="Handicrafts",        requested_amount=95000,   matched_scheme="NSFDC Micro Finance",   readiness_score=50,  status="Pending",      submitted_on="2024-08-11", category="SC", annual_income=120000),
    AdminApplication(id="APP-007", applicant_name="Dilip Biswas",    domain="Trade & Commerce",   requested_amount=450000,  matched_scheme="NSFDC Term Loan",       readiness_score=85,  status="Sanctioned",   submitted_on="2024-08-13", category="SC", annual_income=240000),
    AdminApplication(id="APP-008", applicant_name="Mamata Roy",      domain="Agriculture",        requested_amount=130000,  matched_scheme="NSFDC Micro Finance",   readiness_score=30,  status="Pending",      submitted_on="2024-08-15", category="SC", annual_income=90000),
]


@router.get("/admin/applications", response_model=List[AdminApplication],
            summary="List all submitted applications (admin)",
            dependencies=[Depends(require_role("bank_admin"))])
def admin_get_applications():
    return MOCK_ADMIN_APPLICATIONS


# ────────────────────────────────────────────────────────────────────────────
# POST /api/admin/simulate-npa
# ────────────────────────────────────────────────────────────────────────────

class SimulateNPARequest(BaseModel):
    partner_id: str
    npa_percentage: float = Field(..., ge=0.0, le=100.0)


class SimulateNPAResponse(BaseModel):
    success: bool
    partner_id: str
    partner_name: str
    old_npa: float
    new_npa: float
    is_active: bool
    message: str


@router.post("/admin/simulate-npa", response_model=SimulateNPAResponse,
             summary="Simulate NPA change for a partner (demo)",
             dependencies=[Depends(require_role("bank_admin"))])
def simulate_npa(req: SimulateNPARequest, db: Session = Depends(get_db)):
    partner = db.query(models.ChannelPartner).filter(models.ChannelPartner.id == req.partner_id).first()
    if not partner:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Channel partner '{req.partner_id}' not found.")

    old_npa = partner.npa_percentage
    partner.npa_percentage = req.npa_percentage

    # Auto-deactivate if NPA crosses 8% threshold; reactivate below
    was_active = partner.is_active
    partner.is_active = req.npa_percentage <= 8.0

    db.commit()
    db.refresh(partner)

    if req.npa_percentage > 8.0:
        msg = (
            f"NPA {req.npa_percentage:.1f}% exceeds 8% threshold. "
            "Partner marked INACTIVE — geospatial router will bypass this branch."
        )
    else:
        msg = f"NPA {req.npa_percentage:.1f}% is within healthy range. Partner remains ACTIVE."

    return SimulateNPAResponse(
        success=True,
        partner_id=partner.id,
        partner_name=partner.name,
        old_npa=old_npa,
        new_npa=partner.npa_percentage,
        is_active=partner.is_active,
        message=msg,
    )
