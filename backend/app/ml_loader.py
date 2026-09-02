"""
ml_loader.py – Singleton loader for the GradientBoosting loan-readiness model.

Usage (anywhere in the app):
    from app.ml_loader import get_readiness_score, MODEL_READY
"""

import json
import logging
from pathlib import Path
from typing import Optional

import joblib
import pandas as pd

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
_BASE = Path(__file__).parent.parent          # /backend
_MODEL_PATH = _BASE / "ml_models" / "loan_model.joblib"
_META_PATH  = _BASE / "ml_models" / "model_meta.json"

# ── Module-level singletons (loaded once on first import) ─────────────────────
_pipeline = None
_meta: dict = {}
MODEL_READY: bool = False

try:
    _pipeline = joblib.load(_MODEL_PATH)
    with open(_META_PATH) as f:
        _meta = json.load(f)
    MODEL_READY = True
    logger.info("ML model loaded from %s", _MODEL_PATH)
except FileNotFoundError:
    logger.warning(
        "ML model not found at %s. "
        "Run `python train_model.py` inside the container to generate it. "
        "Falling back to rule-based readiness scoring.",
        _MODEL_PATH,
    )
except Exception as exc:
    logger.exception("Unexpected error loading ML model: %s", exc)


# ── Feature importance map (used for gap analysis) ────────────────────────────
_importance: dict[str, float] = _meta.get("importance_map", {})

# Importance thresholds – features whose combined contribution explains most
# of the score suppression are surfaced as gap recommendations.
_NUMERIC_FEATURES    = _meta.get("numeric_features", [])
_CATEGORICAL_FEATURES = _meta.get("categorical_features", [])


def _build_feature_row(
    age: int,
    annual_income: float,
    requested_amount: float,
    has_udyam: bool,
    has_caste_cert: bool,
    has_income_cert: bool,
    partner_npa: float,
    category: str,
) -> pd.DataFrame:
    """Return a single-row DataFrame matching the training schema."""
    return pd.DataFrame([{
        "age":              float(age),
        "annual_income":    float(annual_income),
        "requested_amount": float(requested_amount),
        "has_udyam":        float(has_udyam),
        "has_caste_cert":   float(has_caste_cert),
        "has_income_cert":  float(has_income_cert),
        "partner_npa":      float(partner_npa),
        "category":         category,
    }])


def get_readiness_score(
    age: int,
    annual_income: float,
    requested_amount: float,
    has_udyam: bool,
    has_caste_cert: bool,
    has_income_cert: bool,
    partner_npa: float = 5.0,          # default healthy NPA when no partner found
    category: str = "SC",
) -> tuple[int, list[str]]:
    """
    Return (readiness_score 0-100, gap_list).

    If the model is not available, falls back to the deterministic rule engine
    and returns (rule_score, rule_gaps).
    """
    if not MODEL_READY or _pipeline is None:
        return _rule_based_fallback(
            requested_amount, has_udyam, has_caste_cert, has_income_cert
        )

    X = _build_feature_row(
        age, annual_income, requested_amount,
        has_udyam, has_caste_cert, has_income_cert,
        partner_npa, category,
    )

    prob = float(_pipeline.predict_proba(X)[0][1])
    score = int(round(prob * 100))

    gaps = _derive_gaps(
        score=prob,
        has_udyam=has_udyam,
        has_caste_cert=has_caste_cert,
        has_income_cert=has_income_cert,
        requested_amount=requested_amount,
        annual_income=annual_income,
        partner_npa=partner_npa,
    )

    return score, gaps


# ── Gap analysis: importance-weighted, contextual ────────────────────────────
def _derive_gaps(
    score: float,
    has_udyam: bool,
    has_caste_cert: bool,
    has_income_cert: bool,
    requested_amount: float,
    annual_income: float,
    partner_npa: float,
) -> list[str]:
    """
    Produce an ordered list of actionable recommendations, prioritised by
    the feature's importance weight in the trained model so the most
    impactful gaps surface first.
    """
    candidates: list[tuple[float, str]] = []

    def _imp(key: str) -> float:
        return _importance.get(key, 0.0)

    # ── Certificate gaps ──────────────────────────────────────────────────────
    if not has_caste_cert:
        candidates.append((
            _imp("has_caste_cert"),
            "Caste Certificate verification pending. "
            "Submit SC certificate issued by a competent authority "
            "(Tehsildar / SDM). This is the highest-weight approval factor.",
        ))

    if not has_income_cert:
        candidates.append((
            _imp("has_income_cert"),
            "Income Certificate not attached. "
            "Obtain from your Tehsildar / SDM office — required to verify "
            "the ₹3,00,000 annual income ceiling.",
        ))

    if not has_udyam and requested_amount > 100_000:
        candidates.append((
            _imp("has_udyam"),
            "MSME Udyam Registration missing (mandatory for loans > ₹1 Lakh). "
            "Register free at https://udyamregistration.gov.in — "
            "typically processed within 1 working day.",
        ))

    # ── Financial health gaps ─────────────────────────────────────────────────
    if requested_amount > 0:
        dti = requested_amount / (annual_income + 1)
        if dti > 5:
            candidates.append((
                _imp("requested_amount") + _imp("annual_income"),
                f"Requested amount (₹{requested_amount:,.0f}) is "
                f"{dti:.1f}× your annual income. "
                "Consider a lower loan amount or a co-applicant to reduce risk.",
            ))

    # ── Partner NPA risk ──────────────────────────────────────────────────────
    if partner_npa > 6.0:
        candidates.append((
            _imp("partner_npa"),
            f"Assigned channel partner NPA is {partner_npa:.1f}% "
            "(above healthy 6% threshold). "
            "Requesting a reassignment to a lower-NPA branch may improve approval odds.",
        ))

    # ── Score-based generic nudge (only when score is low but no specific gap) ─
    if score < 0.55 and not candidates:
        candidates.append((
            0.0,
            "Application risk score is below threshold. "
            "Strengthen your profile by completing all document requirements "
            "and reducing the loan amount if possible.",
        ))

    # Sort descending by feature importance so most impactful gap is first
    candidates.sort(key=lambda x: -x[0])
    return [msg for _, msg in candidates]


# ── Deterministic fallback (mirrors original rule engine) ─────────────────────
def _rule_based_fallback(
    requested_amount: float,
    has_udyam: bool,
    has_caste_cert: bool,
    has_income_cert: bool,
) -> tuple[int, list[str]]:
    score = 100
    gaps: list[str] = []

    if requested_amount > 100_000 and not has_udyam:
        score -= 20
        gaps.append(
            "MSME Udyam Registration missing (Mandatory for loans > ₹1 Lakh). "
            "Register free at https://udyamregistration.gov.in"
        )
    if not has_income_cert:
        score -= 20
        gaps.append(
            "Income Certificate not attached. Obtain from your Tehsildar / SDM office."
        )
    if not has_caste_cert:
        score -= 30
        gaps.append(
            "Caste Certificate verification pending. "
            "Submit SC certificate issued by competent authority."
        )

    return max(0, score), gaps
