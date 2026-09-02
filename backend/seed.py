"""
seed.py – Populate UdyamSetu PostgreSQL/PostGIS DB with initial data.
Run from the /backend directory:
    python seed.py
"""

import sys
import uuid
from pathlib import Path

# Ensure app package is importable when running from /backend
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.database import Base, SessionLocal, engine
from app.models import Scheme, ChannelPartner, User, LoanApplication

# --------------------------------------------------------------------------- #
# Bootstrap tables
# --------------------------------------------------------------------------- #
Base.metadata.create_all(bind=engine)

db = SessionLocal()


def _uid() -> str:
    return str(uuid.uuid4())


def _make_point(lng: float, lat: float) -> str:
    """Return a WKT expression string for a PostGIS geometry point."""
    # We pass this as a raw SQL expression via text() during insert.
    return f"ST_SetSRID(ST_MakePoint({lng}, {lat}), 4326)"


# --------------------------------------------------------------------------- #
# 1. Schemes (no geometry — unchanged)
# --------------------------------------------------------------------------- #
SCHEMES = [
    Scheme(
        id=_uid(),
        name="NSFDC Micro Finance",
        min_amount=0.0,
        max_amount=140_000.0,       # ₹1,40,000
        max_income=300_000.0,        # ₹3,00,000
        base_interest_rate=6.5,
        min_moratorium_months=3,
        max_moratorium_months=6,
        required_category="SC",
        description=(
            "Short-term micro-finance facility for SC beneficiaries to support "
            "micro-enterprises, petty trade, and self-employment activities. "
            "Maximum loan ₹1,40,000 at 6.5% p.a. with a 3-6 month moratorium period."
        ),
    ),
    Scheme(
        id=_uid(),
        name="NSFDC Term Loan",
        min_amount=0.0,
        max_amount=5_000_000.0,     # ₹50,00,000
        max_income=300_000.0,
        base_interest_rate=8.0,
        min_moratorium_months=6,
        max_moratorium_months=12,
        required_category="SC",
        description=(
            "Medium-to-large term loan for SC entrepreneurs to set up or expand "
            "income-generating projects such as small manufacturing units, service "
            "centres, or agri-allied activities. Maximum loan ₹50,00,000 at 8.0% p.a."
        ),
    ),
    Scheme(
        id=_uid(),
        name="NSFDC Education Loan",
        min_amount=0.0,
        max_amount=3_000_000.0,     # ₹30,00,000
        max_income=300_000.0,
        base_interest_rate=4.0,
        min_moratorium_months=12,   # 12 months post-study (represented as minimum)
        max_moratorium_months=12,
        required_category="SC",
        description=(
            "Education loan for SC students pursuing higher education or professional "
            "courses in India and abroad. Maximum loan ₹30,00,000 at concessional "
            "4.0% p.a. with moratorium up to course completion + 12 months."
        ),
    ),
]

# --------------------------------------------------------------------------- #
# 2. Channel Partners – location stored as PostGIS geometry
# --------------------------------------------------------------------------- #
# Raw partner data: (name, partner_type, lat, lng, npa_pct, is_active, phone, email)
_PARTNER_DATA = [
    # ── Healthy branches (NPA < 6%, is_active = True) ──────────────────────
    (
        "Nadia District Co-operative Bank – Kalyani Branch",
        "PSB", 22.975, 88.434, 3.2, True,
        "+91-3472-271001", "kalyani.ndcb@psb.in",
    ),
    (
        "Bangiya Gramin Vikash Bank – Chakdaha Branch",
        "RRB", 23.080, 88.519, 5.1, True,
        "+91-3472-264500", "chakdaha.bgvb@rrb.in",
    ),
    (
        "Arohan Financial Services – Ranaghat Service Centre",
        "NBFC-MFI", 23.177, 88.554, 2.8, True,
        "+91-33-4040-7070", "ranaghat.arohan@nbfc-mfi.in",
    ),
    (
        "West Bengal SC/ST Development & Finance Corporation – Bongaon Desk",
        "SCA", 23.045, 88.823, 4.5, True,
        "+91-3215-255100", "bongaon.wbscdfc@sca.gov.in",
    ),
    # ── Overdue / High-NPA branches (NPA > 12%, is_active = False) ──────────
    (
        "Srei Infrastructure Finance – Haringhata Sub-office",
        "NBFC-MFI", 22.964, 88.560, 18.7, False,
        "+91-33-6602-3456", "haringhata.srei@nbfc-mfi.in",
    ),
    (
        "Gaighata Rural Bank – Gaighata Branch",
        "RRB", 22.859, 88.741, 14.3, False,
        "+91-3216-242200", "gaighata.grb@rrb.in",
    ),
]

# --------------------------------------------------------------------------- #
# 3. Sample Users – location stored as PostGIS geometry
# --------------------------------------------------------------------------- #
# Raw user data: (name, age, gender, category, annual_income, project_domain,
#                 requested_amount, lat, lng, has_udyam, has_caste_cert,
#                 has_income_cert, role)
_USER_DATA = [
    (
        "Rajesh Kumar", 35, "Male", "SC", 180_000.0,
        "Tailoring", 50_000.0,
        22.990, 88.460, True, True, True, "citizen",
    ),
    (
        "Sunita Devi", 28, "Female", "SC", 220_000.0,
        "Food Processing", 120_000.0,
        23.010, 88.490, True, True, True, "citizen",
    ),
    (
        "Mohan Das", 42, "Male", "SC", 250_000.0,
        "Animal Husbandry", 350_000.0,
        23.050, 88.530, False, True, False, "citizen",
    ),
    (
        "Admin User", 30, "Male", "SC", 0.0,
        "Administration", 0.0,
        22.960, 88.410, False, False, False, "bank_admin",
    ),
]

# --------------------------------------------------------------------------- #
# Insert – skip if data already present to allow idempotent re-runs
# --------------------------------------------------------------------------- #
existing_schemes = db.query(Scheme).count()
existing_partners = db.query(ChannelPartner).count()
existing_users = db.query(User).count()

existing_applications = db.query(LoanApplication).count()

# ── Schemes ──────────────────────────────────────────────────────────────────
if existing_schemes == 0:
    db.add_all(SCHEMES)
    db.flush()
    print(f"[OK] Inserted {len(SCHEMES)} schemes.")
else:
    print(f"[SKIP] Schemes already seeded ({existing_schemes} rows).")

# ── Channel Partners (via raw SQL to use ST_SetSRID / ST_MakePoint) ──────────
if existing_partners == 0:
    for (name, p_type, lat, lng, npa, active, phone, email) in _PARTNER_DATA:
        db.execute(
            text("""
                INSERT INTO channel_partners
                    (id, name, partner_type, location,
                     npa_percentage, is_active, contact_phone, contact_email)
                VALUES (
                    :id, :name, :p_type,
                    ST_SetSRID(ST_MakePoint(:lng, :lat), 4326),
                    :npa, :active, :phone, :email
                )
            """),
            {
                "id": _uid(), "name": name, "p_type": p_type,
                "lat": lat, "lng": lng,
                "npa": npa, "active": active,
                "phone": phone, "email": email,
            },
        )
    print(f"[OK] Inserted {len(_PARTNER_DATA)} channel partners.")
else:
    print(f"[SKIP] Channel partners already seeded ({existing_partners} rows).")

# ── Sample Users (via raw SQL to use ST_SetSRID / ST_MakePoint) ──────────────
if existing_users == 0:
    for (name, age, gender, cat, income, domain,
         amount, lat, lng, udyam, caste, inc_cert, role) in _USER_DATA:
        db.execute(
            text("""
                INSERT INTO users
                    (id, name, age, gender, category, annual_income,
                     project_domain, requested_amount, location,
                     readiness_score, has_udyam, has_caste_cert,
                     has_income_cert, hashed_password, role)
                VALUES (
                    :id, :name, :age, :gender, :cat, :income,
                    :domain, :amount,
                    ST_SetSRID(ST_MakePoint(:lng, :lat), 4326),
                    0.0, :udyam, :caste, :inc_cert, NULL, :role
                )
            """),
            {
                "id": _uid(), "name": name, "age": age,
                "gender": gender, "cat": cat, "income": income,
                "domain": domain, "amount": amount,
                "lat": lat, "lng": lng,
                "udyam": udyam, "caste": caste, "inc_cert": inc_cert,
                "role": role,
            },
        )
    print(f"[OK] Inserted {len(_USER_DATA)} sample users.")
else:
    print(f"[SKIP] Users already seeded ({existing_users} rows).")

# ── Sample Loan Applications ──────────────────────────────────────────────────
if existing_applications == 0:
    all_schemes = db.query(Scheme).all()
    all_partners = db.query(ChannelPartner).all()
    all_users = db.query(User).filter(User.role == 'citizen').all()

    if all_schemes and all_partners and all_users:
        applications = [
            LoanApplication(
                id=_uid(),
                user_id=all_users[0].id,
                scheme_id=all_schemes[0].id,
                partner_id=all_partners[0].id,
                amount=50000.0,
                tenure_months=24,
                moratorium_months=3,
                status="Pending"
            ),
            LoanApplication(
                id=_uid(),
                user_id=all_users[1].id,
                scheme_id=all_schemes[1].id,
                partner_id=all_partners[1].id,
                amount=120000.0,
                tenure_months=36,
                moratorium_months=6,
                status="Approved"
            )
        ]
        db.add_all(applications)
        print(f"[OK] Inserted {len(applications)} loan applications.")
else:
    print(f"[SKIP] Loan applications already seeded ({existing_applications} rows).")

db.commit()
db.close()

print("\n[DONE] Seed complete. Database is ready.")
