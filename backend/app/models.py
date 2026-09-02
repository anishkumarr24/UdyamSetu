import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Enum, Float, Integer, String
from geoalchemy2 import Geometry
from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String, nullable=False)
    # 'SC' | 'ST' | 'OBC' | 'General'
    category = Column(String, nullable=False)
    annual_income = Column(Float, nullable=False)
    project_domain = Column(String, nullable=False)
    requested_amount = Column(Float, nullable=False)
    location = Column(Geometry(geometry_type='POINT', srid=4326), nullable=True)
    readiness_score = Column(Float, nullable=False, default=0.0)
    has_udyam = Column(Boolean, nullable=False, default=False)
    has_caste_cert = Column(Boolean, nullable=False, default=False)
    has_income_cert = Column(Boolean, nullable=False, default=False)
    hashed_password = Column(String, nullable=True)
    role = Column(Enum('citizen', 'bank_admin', name='user_role'), nullable=False, default='citizen')


class Scheme(Base):
    __tablename__ = "schemes"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    min_amount = Column(Float, nullable=False, default=0.0)
    max_amount = Column(Float, nullable=False)
    max_income = Column(Float, nullable=False)
    base_interest_rate = Column(Float, nullable=False)
    min_moratorium_months = Column(Integer, nullable=False)
    max_moratorium_months = Column(Integer, nullable=False)
    required_category = Column(String, nullable=False)
    description = Column(String, nullable=False, default="")


class ChannelPartner(Base):
    __tablename__ = "channel_partners"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    # 'SCA' | 'PSB' | 'RRB' | 'NBFC-MFI'
    partner_type = Column(String, nullable=False)
    location = Column(Geometry(geometry_type='POINT', srid=4326), nullable=True)
    npa_percentage = Column(Float, nullable=False, default=0.0)
    is_active = Column(Boolean, nullable=False, default=True)
    contact_phone = Column(String, nullable=False, default="")
    contact_email = Column(String, nullable=False, default="")


class LoanApplication(Base):
    __tablename__ = "loan_applications"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, nullable=False)
    scheme_id = Column(String, nullable=False)
    partner_id = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    tenure_months = Column(Integer, nullable=False)
    moratorium_months = Column(Integer, nullable=False)
    # 'Pending' | 'Under_Review' | 'Approved' | 'Disbursed'
    status = Column(String, nullable=False, default="Pending")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
