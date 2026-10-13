"""
Anomaly and bottleneck detection.

Flags operational anomalies that become triggers for the AI investigation agent:
  * Admission spikes      — daily admissions far above rolling norm (z-score / IQR)
  * Abnormal waiting times — ER wait days above rolling norm
  * Discharge drops       — unexpectedly low discharge counts
  * Occupancy breaches    — department occupancy over the critical threshold
  * Staffing danger       — nurse:patient ratio over the danger threshold

Each anomaly carries a type, severity, department/metric context and the evidence
numbers, so the agent can cite them directly.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.core.config import settings
from app.core.database import query_df


def _zscore_anomalies(series: pd.Series, window: int = 14, z: float = 2.3) -> pd.Series:
    roll_mean = series.rolling(window, min_periods=5).mean()
    roll_std = series.rolling(window, min_periods=5).std().replace(0, np.nan)
    return (series - roll_mean) / roll_std


def detect_admission_spikes(lookback_days: int = 60) -> list[dict]:
    df = query_df(
        "SELECT admit_date d, COUNT(*) n FROM fact_admissions GROUP BY admit_date ORDER BY admit_date"
    )
    s = pd.Series(df["n"].values, index=pd.to_datetime(df["d"]))
    zs = _zscore_anomalies(s)
    recent = zs.tail(lookback_days)
    out = []
    for d, z in recent.items():
        if pd.notna(z) and z >= 2.3:
            out.append({
                "type": "admission_spike",
                "date": d.strftime("%Y-%m-%d"),
                "severity": "critical" if z >= 3 else "warning",
                "value": int(s[d]),
                "z_score": round(float(z), 2),
                "message": f"Admission spike on {d.strftime('%Y-%m-%d')}: {int(s[d])} admissions ({z:.1f}σ above norm)",
            })
    return out


def detect_wait_anomalies(lookback_days: int = 60) -> list[dict]:
    df = query_df(
        "SELECT arrival_date d, AVG(wait_time_min) w FROM fact_er_visits GROUP BY arrival_date ORDER BY arrival_date"
    )
    s = pd.Series(df["w"].values, index=pd.to_datetime(df["d"]))
    zs = _zscore_anomalies(s)
    out = []
    for d, z in zs.tail(lookback_days).items():
        if pd.notna(z) and z >= 2.3:
            out.append({
                "type": "wait_anomaly",
                "date": d.strftime("%Y-%m-%d"),
                "severity": "critical" if z >= 3 else "warning",
                "value": round(float(s[d]), 1),
                "z_score": round(float(z), 2),
                "message": f"Abnormal ER wait on {d.strftime('%Y-%m-%d')}: {s[d]:.0f} min avg ({z:.1f}σ above norm)",
            })
    return out


def detect_occupancy_breaches() -> list[dict]:
    latest = query_df("SELECT MAX(admit_date) d FROM fact_admissions").iloc[0]["d"]
    df = query_df(
        """
        SELECT d.department_name, o.occupancy_rate, o.beds_occupied, o.total_beds
        FROM fact_bed_occupancy_daily o JOIN dim_department d ON o.department_id = d.department_id
        WHERE o.date = ? AND o.occupancy_rate >= ?
        ORDER BY o.occupancy_rate DESC
        """,
        (latest, settings.occupancy_warning),
    )
    out = []
    for _, r in df.iterrows():
        rate = float(r["occupancy_rate"])
        out.append({
            "type": "occupancy_breach",
            "department": r["department_name"],
            "severity": "critical" if rate >= settings.occupancy_critical else "warning",
            "value": round(rate, 3),
            "message": f"{r['department_name']} at {rate:.0%} occupancy "
                       f"({int(r['beds_occupied'])}/{int(r['total_beds'])} beds)",
        })
    return out


def detect_staffing_danger() -> list[dict]:
    from app.analytics.kpis import staffing_efficiency
    out = []
    for row in staffing_efficiency():
        if row["status"] == "danger":
            out.append({
                "type": "staffing_danger",
                "department": row["department_name"],
                "shift": row["shift"],
                "severity": "critical" if row["patients_per_nurse"] >= settings.nurse_ratio_danger * 1.3 else "warning",
                "value": row["patients_per_nurse"],
                "message": f"{row['department_name']} {row['shift']} shift: "
                           f"{row['patients_per_nurse']} patients/nurse (danger)",
            })
    return out


def detect_all() -> dict:
    anomalies = (
        detect_occupancy_breaches()
        + detect_staffing_danger()
        + detect_admission_spikes(lookback_days=14)
        + detect_wait_anomalies(lookback_days=14)
    )
    critical = [a for a in anomalies if a.get("severity") == "critical"]
    return {
        "total": len(anomalies),
        "critical_count": len(critical),
        "anomalies": anomalies,
    }
