"""
digilocker.py – Simulated DigiLocker OAuth + document fetch endpoints.

Routes (mounted at /api/v1):
  GET  /api/v1/digilocker/auth-url          – Return simulated OAuth2 authorization URL.
  POST /api/v1/digilocker/verify-fetch      – Simulate fetching & verifying a document.

Design notes
------------
In a production integration you would:
  1. Redirect the user to the real DigiLocker OAuth URL
     (https://api.digitallocker.gov.in/public/oauth2/1/authorize)
  2. Exchange the authorization code for an access token.
  3. Call the DigiLocker Pull API to fetch the document XML/PDF.
  4. Parse and verify the document's digital signature.

This module provides a faithful simulation of that flow with realistic
response payloads, timestamps, and issuing authority metadata, so the
frontend can be built against a stable contract before live credentials
are obtained.
"""

from datetime import datetime, timezone, timedelta
from typing import Literal, Optional
import hashlib
import uuid

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/digilocker", tags=["digilocker"])


# ────────────────────────────────────────────────────────────────────────────
# Schemas
# ────────────────────────────────────────────────────────────────────────────

class AuthURLResponse(BaseModel):
    auth_url: str
    state: str
    expires_in_seconds: int
    note: str


class VerifyFetchRequest(BaseModel):
    document_type: Literal["udyam", "aadhaar", "caste_cert", "income_cert"]
    # In a real flow this would be the OAuth access_token or auth_code.
    # Here we accept any non-empty string as a simulated token.
    access_token: str
    # Optional applicant hint for building the mock payload
    applicant_name: Optional[str] = None


class IssuerMetadata(BaseModel):
    authority: str
    authority_code: str
    state: str
    verified_by: str


class VerifyFetchResponse(BaseModel):
    success: bool
    document_type: str
    document_id: str
    issuer: IssuerMetadata
    verified_at: str                # ISO-8601
    valid_until: Optional[str]      # ISO-8601 or null
    document_data: dict
    digital_signature_valid: bool
    note: str


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

_DIGILOCKER_BASE = "https://api.digitallocker.gov.in/public/oauth2/1/authorize"
_CLIENT_ID       = "UDYAMSETU_DEMO_CLIENT_ID"          # Replace with real client-id
_REDIRECT_URI    = "http://localhost:8000/api/v1/digilocker/callback"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _future_iso(days: int = 365) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _doc_id(prefix: str, token: str) -> str:
    """Deterministic but opaque document ID derived from the token."""
    h = hashlib.sha256(token.encode()).hexdigest()[:16].upper()
    return f"{prefix}-{h[:4]}-{h[4:8]}-{h[8:12]}-{h[12:]}"


# ── Mock document payloads ─────────────────────────────────────────────────

def _udyam_payload(name: str, doc_id: str) -> dict:
    return {
        "udyam_registration_number": f"UDYAM-WB-12-{doc_id[-7:]}",
        "enterprise_name": name or "M/s Sample Enterprises",
        "owner_name": name or "Rajesh Kumar",
        "enterprise_type": "Micro",
        "major_activity": "Manufacturing",
        "nic_code": "10309",
        "date_of_registration": "2023-04-15",
        "district": "Nadia",
        "state": "West Bengal",
        "pin": "741165",
        "investment_in_plant_machinery_lakh": 4.5,
        "turnover_lakh": 18.2,
    }


def _aadhaar_payload(name: str, doc_id: str) -> dict:
    # Only non-sensitive fields — full Aadhaar number is never returned
    masked_uid = f"XXXX-XXXX-{doc_id[-4:]}"
    return {
        "masked_aadhaar": masked_uid,
        "name": name or "Rajesh Kumar",
        "gender": "M",
        "year_of_birth": "1991",
        "address": {
            "house": "12, Subhas Nagar",
            "street": "Rabindra Sarani",
            "locality": "Kalyani",
            "district": "Nadia",
            "state": "West Bengal",
            "pin": "741235",
        },
    }


def _caste_cert_payload(name: str, doc_id: str) -> dict:
    return {
        "certificate_number": f"WB/SC/{doc_id[-8:]}",
        "holder_name": name or "Rajesh Kumar",
        "father_name": "Ram Kumar",
        "caste": "SC",
        "sub_caste": "Chamar",
        "issuing_tehsil": "Kalyani",
        "district": "Nadia",
        "state": "West Bengal",
        "date_of_issue": "2022-07-20",
    }


def _income_cert_payload(name: str, doc_id: str) -> dict:
    return {
        "certificate_number": f"WB/INC/{doc_id[-8:]}",
        "holder_name": name or "Rajesh Kumar",
        "annual_income_inr": 180000,
        "income_year": "2023-24",
        "purpose": "NSFDC Loan Application",
        "issuing_officer": "Tehsildar, Kalyani",
        "district": "Nadia",
        "state": "West Bengal",
        "date_of_issue": "2024-02-10",
        "valid_until": _future_iso(365),
    }


_PAYLOAD_MAP = {
    "udyam":       (_udyam_payload,      "UDYAM",  "Ministry of MSME, GoI",
                    "MSME-DFO-WB", "West Bengal", "NIC e-Gov Gateway"),
    "aadhaar":     (_aadhaar_payload,    "AADH",   "UIDAI",
                    "UIDAI-WB",    "West Bengal", "UIDAI e-KYC Service"),
    "caste_cert":  (_caste_cert_payload, "CAST",   "Office of the SDM / Tehsildar",
                    "SDM-NADIA",   "West Bengal", "DigiLocker Issuer API"),
    "income_cert": (_income_cert_payload,"INCC",   "Office of the SDM / Tehsildar",
                    "SDM-NADIA",   "West Bengal", "DigiLocker Issuer API"),
}


# ────────────────────────────────────────────────────────────────────────────
# Endpoints
# ────────────────────────────────────────────────────────────────────────────

@router.get(
    "/auth-url",
    response_model=AuthURLResponse,
    summary="Get simulated DigiLocker OAuth2 authorization URL",
)
def get_auth_url(
    redirect_uri: str = Query(
        default=_REDIRECT_URI,
        description="OAuth redirect URI (override for your frontend origin)",
    ),
):
    state = str(uuid.uuid4())
    params = (
        f"response_type=code"
        f"&client_id={_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
        f"&scope=files.issueddocument.all"
    )
    auth_url = f"{_DIGILOCKER_BASE}?{params}"

    return AuthURLResponse(
        auth_url=auth_url,
        state=state,
        expires_in_seconds=600,
        note=(
            "SIMULATION MODE — This URL uses a demo client_id. "
            "Replace UDYAMSETU_DEMO_CLIENT_ID with a registered DigiLocker "
            "application client-id before going to production."
        ),
    )


@router.post(
    "/verify-fetch",
    response_model=VerifyFetchResponse,
    summary="Simulate DigiLocker document fetch and verification",
)
def verify_and_fetch_document(doc_type: str = "udyam"):
    if doc_type not in _PAYLOAD_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown document_type '{doc_type}'. "
                   f"Supported: {list(_PAYLOAD_MAP.keys())}",
        )

    payload_fn, id_prefix, authority, auth_code, state, verifier = _PAYLOAD_MAP[doc_type]

    # In simulation mode, we just use a dummy token and no applicant name
    dummy_token = "dummy_token_12345"
    doc_id = _doc_id(id_prefix, dummy_token)
    applicant = None
    doc_data  = payload_fn(applicant, doc_id)

    # Income cert has its own valid_until in the payload; others 1 year
    valid_until = doc_data.get("valid_until", _future_iso(365))

    return VerifyFetchResponse(
        success=True,
        document_type=doc_type,
        document_id=doc_id,
        issuer=IssuerMetadata(
            authority=authority,
            authority_code=auth_code,
            state=state,
            verified_by=verifier,
        ),
        verified_at=_now_iso(),
        valid_until=valid_until,
        document_data=doc_data,
        digital_signature_valid=True,
        note=(
            "SIMULATION MODE — Document data is synthetic. "
            "In production, this data is fetched from the DigiLocker Pull API "
            "and verified against the issuer's digital signature."
        ),
    )
