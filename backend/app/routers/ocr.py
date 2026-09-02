"""
ocr.py – Document image parsing via Tesseract OCR.

Routes (mounted at /api/v1):
  POST /api/v1/ocr/extract   – Upload an image; returns raw OCR text + parsed fields.

Parsing strategy
----------------
The regex patterns target the bilingual layout of common Indian government
certificates (Caste, Income, Udyam). Pattern priority:
  1. English label → value on same line or next line
  2. Hindi Devanagari label → value on same line
  3. Fallback: heuristic numeric / uppercase-word extraction
"""

import io
import re
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel
from PIL import Image
import pytesseract

router = APIRouter(prefix="/ocr", tags=["ocr"])


# ── Response schema ────────────────────────────────────────────────────────────

class ParsedFields(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    category: Optional[str] = None
    annual_income: Optional[str] = None
    registration_number: Optional[str] = None
    date_of_issue: Optional[str] = None


class OCRExtractResponse(BaseModel):
    extracted_text: str
    parsed_fields: ParsedFields
    confidence_note: str


# ── Regex helpers ──────────────────────────────────────────────────────────────

# Matches "Name : Rajesh Kumar" / "Name- Rajesh Kumar" / inline Hindi
_NAME_RE = re.compile(
    r"(?:Name|नाम|Naam)\s*[:\-–]\s*([A-Za-z][A-Za-z\s\.]{2,50})",
    re.IGNORECASE,
)

# Caste / Category: SC, ST, OBC, General (and Hindi equivalents)
_CATEGORY_RE = re.compile(
    r"(?:Caste|Category|जाति|वर्ग)\s*[:\-–]?\s*"
    r"(SC|ST|OBC|General|अनुसूचित\s*जाति|अनुसूचित\s*जनजाति|पिछड़ा\s*वर्ग)",
    re.IGNORECASE,
)

# Income amounts: "Rs. 1,80,000" / "₹ 2,40,000 per annum" / "Income: 150000"
_INCOME_RE = re.compile(
    r"(?:Annual\s*Income|Income|आय)\s*[:\-–]?\s*"
    r"(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{1,2})?)",
    re.IGNORECASE,
)

# Age / DOB
_AGE_RE = re.compile(
    r"(?:Age|आयु|उम्र)\s*[:\-–]?\s*(\d{1,3})",
    re.IGNORECASE,
)
_DOB_RE = re.compile(
    r"(?:DOB|Date of Birth|जन्म तिथि)\s*[:\-–]?\s*"
    r"(\d{2}[/\-]\d{2}[/\-]\d{4}|\d{4}[/\-]\d{2}[/\-]\d{2})",
    re.IGNORECASE,
)

# Gender
_GENDER_RE = re.compile(
    r"(?:Gender|Sex|लिंग)\s*[:\-–]?\s*(Male|Female|Transgender|Other|पुरुष|महिला|अन्य)",
    re.IGNORECASE,
)

# Udyam / Registration numbers:  UDYAM-WB-12-0012345, Reg. No. ABC/2024/123
_REG_RE = re.compile(
    r"(?:"
    r"UDYAM-[A-Z]{2}-\d{2}-\d{7}"          # Udyam format
    r"|[A-Z]{2,5}/\d{4}/\d{3,10}"          # Generic GOI format
    r"|\bReg(?:istration)?\.?\s*No\.?\s*[:\-]?\s*([A-Z0-9/\-]{6,25})"
    r")",
    re.IGNORECASE,
)

# Date: DD/MM/YYYY or DD-MM-YYYY or YYYY-MM-DD
_DATE_RE = re.compile(
    r"\b(\d{2}[/\-]\d{2}[/\-]\d{4}|\d{4}[/\-]\d{2}[/\-]\d{2})\b"
)


def _first_group(pattern: re.Pattern, text: str) -> Optional[str]:
    """Return stripped first capture group, or the full match if no groups."""
    m = pattern.search(text)
    if not m:
        return None
    hit = m.group(1) if m.lastindex else m.group(0)
    return hit.strip() if hit else None


def _parse_text(text: str) -> ParsedFields:
    # Name: strip trailing noise (numbers, punctuation)
    raw_name = _first_group(_NAME_RE, text)
    clean_name: Optional[str] = None
    if raw_name:
        clean_name = re.sub(r"[^A-Za-z\s\.]", "", raw_name).strip()
        clean_name = clean_name if len(clean_name) > 2 else None

    # Category: normalise Hindi to English label
    raw_cat = _first_group(_CATEGORY_RE, text)
    if raw_cat:
        norm = {
            "अनुसूचित जाति": "SC",
            "अनुसूचित जनजाति": "ST",
            "पिछड़ा वर्ग": "OBC",
        }
        raw_cat = norm.get(raw_cat.strip(), raw_cat.upper().strip())

    # Income: strip commas → plain number string
    raw_income = _first_group(_INCOME_RE, text)
    if raw_income:
        raw_income = raw_income.replace(",", "")

    # Registration number
    reg_no: Optional[str] = None
    m_reg = _REG_RE.search(text)
    if m_reg:
        # Pick whichever group matched (Udyam full-match or generic group-1)
        reg_no = (m_reg.group(1) or m_reg.group(0)).strip()

    # Date of issue (first found)
    date_hit = _first_group(_DATE_RE, text)

    # Age / DOB
    raw_age = _first_group(_AGE_RE, text)
    age_val: Optional[int] = None
    if raw_age:
        try:
            age_val = int(raw_age)
        except ValueError:
            pass
    if not age_val:
        raw_dob = _first_group(_DOB_RE, text)
        if raw_dob:
            m_year = re.search(r'\d{4}', raw_dob)
            if m_year:
                import datetime
                age_val = datetime.datetime.now().year - int(m_year.group(0))

    # Gender
    raw_gender = _first_group(_GENDER_RE, text)
    gender_val: Optional[str] = None
    if raw_gender:
        norm_gender = {
            "पुरुष": "Male",
            "महिला": "Female",
            "अन्य": "Other",
        }
        raw_gender = raw_gender.strip().title()
        gender_val = norm_gender.get(raw_gender, raw_gender)
        if gender_val not in ["Male", "Female", "Transgender", "Other"]:
            if "Male" in gender_val: gender_val = "Male"
            elif "Female" in gender_val: gender_val = "Female"
            else: gender_val = None

    return ParsedFields(
        name=clean_name,
        age=age_val,
        gender=gender_val,
        category=raw_cat,
        annual_income=raw_income,
        registration_number=reg_no,
        date_of_issue=date_hit,
    )


# ── Endpoint ───────────────────────────────────────────────────────────────────

@router.post(
    "/extract",
    response_model=OCRExtractResponse,
    summary="Extract and parse text from a certificate image",
)
async def extract_document(
    file: UploadFile = File(..., description="Certificate image (JPEG/PNG/TIFF)"),
):
    # Validate MIME type
    allowed = {"image/jpeg", "image/png", "image/tiff", "image/bmp", "image/webp"}
    content_type = file.content_type or ""
    if content_type not in allowed:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{content_type}'. "
                   f"Accepted: {', '.join(sorted(allowed))}",
        )

    raw_bytes = await file.read()
    if len(raw_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(raw_bytes) > 10 * 1024 * 1024:  # 10 MB guard
        raise HTTPException(status_code=413, detail="File exceeds 10 MB limit.")

    try:
        image = Image.open(io.BytesIO(raw_bytes))
        # Tesseract with English + Hindi language packs
        extracted_text: str = pytesseract.image_to_string(image, lang="eng+hin")
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"OCR processing failed: {exc}",
        )

    parsed = _parse_text(extracted_text)

    # Compose a human-readable confidence note
    found = [f for f in [parsed.name, parsed.age, parsed.gender, parsed.category, parsed.annual_income,
                         parsed.registration_number, parsed.date_of_issue]
             if f is not None]
    confidence_note = (
        f"Extracted {len(found)}/5 field(s). "
        "For best results supply a high-resolution scan (≥300 DPI) with "
        "clear, unobstructed text."
    )

    return OCRExtractResponse(
        extracted_text=extracted_text,
        parsed_fields=parsed,
        confidence_note=confidence_note,
    )
