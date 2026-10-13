"""
Patient volume forecasting.

Forecasts daily admission volume (overall or per-department) using a lightweight,
robust time-series approach:
  * Holt-Winters exponential smoothing (statsmodels) with weekly seasonality when
    enough history exists.
  * Falls back to a seasonal-naive / moving-average model for short series.

Also provides a shift-level volume breakdown so staffing can be planned per shift.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from app.core.database import query_df

warnings.filterwarnings("ignore")


def _daily_series(department_id: int | None = None) -> pd.Series:
    if department_id is None:
        df = query_df(
            "SELECT admit_date AS d, COUNT(*) n FROM fact_admissions GROUP BY admit_date ORDER BY admit_date"
        )
    else:
        df = query_df(
            "SELECT admit_date AS d, COUNT(*) n FROM fact_admissions WHERE department_id = ? GROUP BY admit_date ORDER BY admit_date",
            (department_id,),
        )
    s = pd.Series(df["n"].values, index=pd.to_datetime(df["d"]))
    # fill missing days with 0 so the index is continuous
    full = pd.date_range(s.index.min(), s.index.max(), freq="D")
    return s.reindex(full, fill_value=0)


def forecast_admissions(department_id: int | None = None, horizon: int = 7) -> dict:
    """Forecast daily admissions `horizon` days ahead."""
    s = _daily_series(department_id)
    history = [
        {"date": d.strftime("%Y-%m-%d"), "admissions": int(v)}
        for d, v in s.tail(30).items()
    ]

    model_used = "holt-winters"
    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing

        if len(s) < 21:
            raise ValueError("series too short for seasonal model")
        fit = ExponentialSmoothing(
            s.astype(float),
            trend="add",
            seasonal="add",
            seasonal_periods=7,
            initialization_method="estimated",
        ).fit()
        fc = fit.forecast(horizon)
        resid_std = float(np.std(fit.resid)) if hasattr(fit, "resid") else float(s.std())
    except Exception:
        model_used = "seasonal-naive"
        last_week = s.tail(7).values
        base = np.resize(last_week, horizon)
        trend = np.linspace(0, (s.tail(14).mean() - s.head(14).mean()) / max(1, len(s)), horizon)
        fc = pd.Series(base + trend)
        resid_std = float(s.tail(30).std())

    last_date = s.index.max()
    forecast = []
    for i, val in enumerate(np.asarray(fc), start=1):
        d = (last_date + pd.Timedelta(days=i)).strftime("%Y-%m-%d")
        pt = max(0.0, float(val))
        forecast.append({
            "date": d,
            "predicted_admissions": round(pt, 1),
            "lower": round(max(0.0, pt - 1.96 * resid_std), 1),
            "upper": round(pt + 1.96 * resid_std, 1),
        })

    return {
        "department_id": department_id,
        "model": model_used,
        "horizon_days": horizon,
        "history": history,
        "forecast": forecast,
    }


def forecast_by_shift(department_id: int, horizon_days: int = 2) -> list[dict]:
    """Forecast per-shift admission volume using recent shift-share * daily forecast."""
    shares = query_df(
        "SELECT shift, COUNT(*) n FROM fact_admissions WHERE department_id = ? GROUP BY shift",
        (department_id,),
    )
    total = shares["n"].sum() or 1
    share_map = {r["shift"]: r["n"] / total for _, r in shares.iterrows()}

    daily = forecast_admissions(department_id, horizon=horizon_days)["forecast"]
    out = []
    for day in daily:
        for shift in ("Morning", "Evening", "Night"):
            out.append({
                "date": day["date"],
                "shift": shift,
                "predicted_admissions": round(float(day["predicted_admissions"] * share_map.get(shift, 0.33)), 1),
            })
    return out
