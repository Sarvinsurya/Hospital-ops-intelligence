"""
Dynamic waiting-time prediction.

Trains a regression model on the REAL ER Wait Time dataset (fact_er_visits) to
predict total wait time from operational features:
  * urgency level
  * nurse-to-patient ratio
  * ER occupancy proxy
  * shift / time of day
  * specialist availability

The trained model is cached to data/models/ and reused. Exposes a predict()
that the dashboard and the AI agent both call for "what-if" wait estimates.
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from app.core.config import MODELS_DIR
from app.core.database import query_df

MODEL_PATH = MODELS_DIR / "wait_time_model.joblib"
META_PATH = MODELS_DIR / "wait_time_meta.json"

NUM_FEATURES = ["nurse_patient_ratio", "er_occupancy", "specialist_availability"]
CAT_FEATURES = ["urgency", "shift"]
TARGET = "wait_time_min"


def _load_training_frame() -> pd.DataFrame:
    cols = NUM_FEATURES + CAT_FEATURES + [TARGET]
    df = query_df(f"SELECT {', '.join(cols)} FROM fact_er_visits")
    df = df.dropna(subset=[TARGET])
    for c in NUM_FEATURES:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(df[c].median())
    return df


def train(force: bool = False) -> dict:
    """Train and persist the wait-time model. Returns evaluation metrics."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    if MODEL_PATH.exists() and META_PATH.exists() and not force:
        return json.loads(META_PATH.read_text())

    df = _load_training_frame()
    X, y = df[NUM_FEATURES + CAT_FEATURES], df[TARGET].astype(float)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)

    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), CAT_FEATURES),
        ("num", "passthrough", NUM_FEATURES),
    ])
    model = Pipeline([
        ("pre", pre),
        ("gbr", GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.08, random_state=42)),
    ])
    model.fit(X_tr, y_tr)
    pred = model.predict(X_te)
    meta = {
        "model": "GradientBoostingRegressor",
        "trained_on": "real ER Wait Time dataset",
        "n_samples": int(len(df)),
        "mae_min": round(float(mean_absolute_error(y_te, pred)), 2),
        "r2": round(float(r2_score(y_te, pred)), 3),
        "features": NUM_FEATURES + CAT_FEATURES,
    }
    joblib.dump(model, MODEL_PATH)
    META_PATH.write_text(json.dumps(meta, indent=2))
    return meta


def _get_model():
    if not MODEL_PATH.exists():
        train(force=True)
    return joblib.load(MODEL_PATH)


def predict(urgency: str, nurse_patient_ratio: float, er_occupancy: float,
            shift: str = "Morning", specialist_availability: int = 3) -> dict:
    """Predict wait time for a hypothetical ER visit (used by dashboard + agent)."""
    model = _get_model()
    X = pd.DataFrame([{
        "nurse_patient_ratio": float(nurse_patient_ratio),
        "er_occupancy": float(er_occupancy),
        "specialist_availability": int(specialist_availability),
        "urgency": urgency,
        "shift": shift,
    }])
    pred = float(model.predict(X)[0])
    return {
        "predicted_wait_min": round(max(0.0, pred), 1),
        "inputs": X.iloc[0].to_dict(),
    }


def sensitivity_curve(urgency: str = "High", shift: str = "Evening") -> list[dict]:
    """How predicted wait changes as nurse ratio worsens — drives agent staffing advice."""
    model = _get_model()
    out = []
    for ratio in [1, 2, 3, 4, 5]:
        X = pd.DataFrame([{
            "nurse_patient_ratio": ratio,
            "er_occupancy": 0.8,
            "specialist_availability": 3,
            "urgency": urgency,
            "shift": shift,
        }])
        out.append({"nurse_patient_ratio": ratio, "predicted_wait_min": round(float(model.predict(X)[0]), 1)})
    return out
