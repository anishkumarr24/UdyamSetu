"""
train_model.py – Generate synthetic micro-loan data and train a GradientBoostingClassifier.

Features (8):
    age, annual_income, requested_amount, has_udyam, has_caste_cert,
    has_income_cert, partner_npa,
    category_OBC, category_SC, category_ST  (one-hot, General is the reference)

Target:
    approved  (1 = likely approved, 0 = rejected)

Output:
    ml_models/loan_model.joblib   – sklearn Pipeline (preprocessor + classifier)

Run from /backend:
    python train_model.py
"""

import sys
import os
import json
import numpy as np
from pathlib import Path

# ── Make app importable when running standalone ───────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

# ── Deps ─────────────────────────────────────────────────────────────────────
import joblib
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score

# ── Reproducibility ───────────────────────────────────────────────────────────
RNG = np.random.default_rng(42)
N = 2_000

# ────────────────────────────────────────────────────────────────────────────
# 1. Synthetic dataset generation
# ────────────────────────────────────────────────────────────────────────────
print("[1/4] Generating synthetic dataset …")

age             = RNG.integers(18, 66,  size=N).astype(float)
annual_income   = RNG.integers(50_000, 500_001, size=N).astype(float)
requested_amount = RNG.integers(10_000, 1_000_001, size=N).astype(float)
has_udyam       = RNG.integers(0, 2, size=N).astype(float)
has_caste_cert  = RNG.integers(0, 2, size=N).astype(float)
has_income_cert = RNG.integers(0, 2, size=N).astype(float)
partner_npa     = RNG.uniform(0.0, 15.0, size=N)
category        = RNG.choice(["SC", "ST", "OBC", "General"], size=N,
                              p=[0.45, 0.20, 0.25, 0.10])

# ── Approval label: domain-knowledge heuristics + noise ──────────────────────
# Higher income relative to amount → good; having certs → good; SC → bonus;
# high NPA partner → bad; large amount without Udyam → bad.
income_ratio = annual_income / (requested_amount + 1)
cert_score   = has_udyam + has_caste_cert + has_income_cert        # 0-3
npa_penalty  = partner_npa / 15.0                                   # 0-1
sc_bonus     = (category == "SC").astype(float)
amount_risk  = np.clip(requested_amount / 1_000_000, 0, 1)

# Logit-like approval probability
logit = (
    1.5 * np.log1p(income_ratio)
    + 0.8 * cert_score
    - 1.0 * npa_penalty
    + 0.4 * sc_bonus
    - 0.6 * amount_risk
    + RNG.normal(0, 0.3, size=N)          # noise
)
prob_approved = 1 / (1 + np.exp(-logit))
approved = (RNG.random(size=N) < prob_approved).astype(int)

print(f"    Approval rate: {approved.mean()*100:.1f}%")

# ── Assemble feature matrix ───────────────────────────────────────────────────
import pandas as pd

df = pd.DataFrame({
    "age":              age,
    "annual_income":    annual_income,
    "requested_amount": requested_amount,
    "has_udyam":        has_udyam,
    "has_caste_cert":   has_caste_cert,
    "has_income_cert":  has_income_cert,
    "partner_npa":      partner_npa,
    "category":         category,
    "approved":         approved,
})

# ────────────────────────────────────────────────────────────────────────────
# 2. Preprocessing pipeline
# ────────────────────────────────────────────────────────────────────────────
print("[2/4] Building preprocessing + classifier pipeline …")

NUMERIC_FEATURES  = ["age", "annual_income", "requested_amount",
                      "has_udyam", "has_caste_cert", "has_income_cert",
                      "partner_npa"]
CATEGORICAL_FEATURES = ["category"]

preprocessor = ColumnTransformer(
    transformers=[
        ("num", StandardScaler(), NUMERIC_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
    ],
    remainder="drop",
)

clf = GradientBoostingClassifier(
    n_estimators=300,
    max_depth=4,
    learning_rate=0.08,
    subsample=0.8,
    min_samples_leaf=10,
    random_state=42,
)

pipeline = Pipeline([
    ("preprocessor", preprocessor),
    ("classifier",   clf),
])

# ────────────────────────────────────────────────────────────────────────────
# 3. Train / evaluate
# ────────────────────────────────────────────────────────────────────────────
print("[3/4] Training …")

X = df.drop(columns=["approved"])
y = df["approved"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42, stratify=y
)

pipeline.fit(X_train, y_train)

y_pred  = pipeline.predict(X_test)
y_proba = pipeline.predict_proba(X_test)[:, 1]

print("\n── Evaluation on held-out test set (20%) ──────────────────────────────")
print(classification_report(y_test, y_pred, target_names=["Rejected", "Approved"]))
print(f"ROC-AUC: {roc_auc_score(y_test, y_proba):.4f}")

# ── Feature importance mapping (for gap analysis in engine.py) ───────────────
# After fitting, extract feature names from the ColumnTransformer
ohe_names = (
    pipeline["preprocessor"]
    .named_transformers_["cat"]
    .get_feature_names_out(CATEGORICAL_FEATURES)
    .tolist()
)
all_feature_names = NUMERIC_FEATURES + ohe_names

importances = pipeline["classifier"].feature_importances_
importance_map = dict(zip(all_feature_names, importances.tolist()))

print("\n── Feature importances ─────────────────────────────────────────────────")
for feat, imp in sorted(importance_map.items(), key=lambda x: -x[1]):
    print(f"  {feat:<30s} {imp:.4f}")

# ────────────────────────────────────────────────────────────────────────────
# 4. Save artefacts
# ────────────────────────────────────────────────────────────────────────────
print("\n[4/4] Saving artefacts …")

out_dir = Path(__file__).parent / "ml_models"
out_dir.mkdir(exist_ok=True)

model_path = out_dir / "loan_model.joblib"
joblib.dump(pipeline, model_path)
print(f"  Pipeline  → {model_path}")

meta_path = out_dir / "model_meta.json"
with open(meta_path, "w") as f:
    json.dump(
        {
            "feature_names": all_feature_names,
            "numeric_features": NUMERIC_FEATURES,
            "categorical_features": CATEGORICAL_FEATURES,
            "importance_map": importance_map,
            "n_training_samples": N,
            "approval_rate_pct": float(round(approved.mean() * 100, 1)),
        },
        f,
        indent=2,
    )
print(f"  Metadata  → {meta_path}")
print("\n[DONE] Model training complete.")
