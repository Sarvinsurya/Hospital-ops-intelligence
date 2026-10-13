"""
Synthetic hospital operations data generator.

Produces data matching the structure of the two Kaggle datasets referenced in
the project abstract:
  * Hospital Beds Management  -> departments, beds, staffing, admissions
  * ER Wait Time              -> patient visits with wait time, urgency, nurse ratio

The generator embeds realistic operational patterns so the downstream BI/ML/agent
layers have meaningful signal:
  * weekday vs weekend admission rhythm
  * seasonal / weekly surge waves
  * shift-dependent staffing gaps (night shift understaffed)
  * occupancy-driven waiting times (congestion raises waits)
  * urgency-driven triage priority
  * injected anomalies (admission spikes, discharge drops) for anomaly detection

Running this module writes CSVs to data/raw/synthetic/ which the ETL then loads.
"""
from __future__ import annotations

import math
import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from app.core.config import RAW_DIR

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# ---------------------------------------------------------------------------
# Reference dimensions
# ---------------------------------------------------------------------------
DEPARTMENTS = [
    # name, base_beds, target_occupancy, avg_los_days, emergency_share
    # The first 4 mirror the REAL "Hospital Beds Management" services (beds & ALOS
    # calibrated from data/raw/hospital_beds). The rest are complementary wards that
    # keep the operational control-room rich while staying clinically plausible.
    #   adm_per_day = beds * target_occ / avg_los   (Little's Law)
    ("Emergency",        32, 0.90, 2.0, 0.95),   # real service (ER los capped lower for flow)
    ("General Medicine", 46, 0.88, 6.5, 0.45),   # real service
    ("Surgery",          38, 0.84, 7.0, 0.30),   # real service
    ("ICU",              16, 0.92, 7.5, 0.80),   # real service
    ("Cardiology",       28, 0.83, 5.0, 0.40),
    ("Pediatrics",       26, 0.70, 3.0, 0.55),
    ("Orthopedics",      24, 0.80, 4.5, 0.35),
    ("Maternity",        22, 0.62, 2.5, 0.25),
]

SHIFTS = ["Morning", "Evening", "Night"]  # 06-14, 14-22, 22-06
SHIFT_HOURS = {"Morning": (6, 14), "Evening": (14, 22), "Night": (22, 30)}
URGENCY_LEVELS = ["Critical", "High", "Medium", "Low"]
URGENCY_WEIGHTS = [0.08, 0.22, 0.42, 0.28]
ADMISSION_TYPES = ["Emergency", "Elective"]

N_DAYS = 180
START_DATE = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=N_DAYS - 1)


def _seasonal_multiplier(day_index: int) -> float:
    """Weekly wave + slow upward trend + occasional surge."""
    weekly = 1.0 + 0.10 * math.sin(2 * math.pi * day_index / 7.0)
    trend = 1.0 + 0.0008 * day_index
    return weekly * trend


def _weekday_multiplier(dt: datetime) -> float:
    # Weekends: fewer electives, slightly more emergencies overall lower
    return 0.82 if dt.weekday() >= 5 else 1.05


def generate_departments() -> pd.DataFrame:
    rows = []
    for i, (name, beds, target_occ, los, emerg) in enumerate(DEPARTMENTS, start=1):
        # Derive admissions/day from target occupancy (Little's Law: L = λ·W)
        adm_per_day = beds * target_occ / los
        rows.append({
            "department_id": i,
            "department_name": name,
            "total_beds": beds,
            "target_occupancy": target_occ,
            "avg_length_of_stay": los,
            "adm_per_day": round(adm_per_day, 3),
            "emergency_share": emerg,
            "facility_wing": random.choice(["North", "South", "East", "West"]),
        })
    return pd.DataFrame(rows)


def generate_staffing(dept_df: pd.DataFrame) -> pd.DataFrame:
    """Nurse roster per department per shift per day."""
    rows = []
    staff_id = 1
    for day in range(N_DAYS):
        dt = START_DATE + timedelta(days=day)
        for _, d in dept_df.iterrows():
            # base nurses scale with beds; night shift deliberately leaner (gap signal)
            base = max(2, round(d["total_beds"] / 8))
            for shift in SHIFTS:
                factor = {"Morning": 1.0, "Evening": 0.85, "Night": 0.6}[shift]
                nurses = max(1, int(round(base * factor + np.random.randint(-1, 2))))
                # inject periodic understaffing on night shift for ICU/Emergency
                if shift == "Night" and d["department_name"] in ("ICU", "Emergency") and day % 9 == 0:
                    nurses = max(1, nurses - 2)
                rows.append({
                    "staffing_id": staff_id,
                    "date": dt.strftime("%Y-%m-%d"),
                    "department_id": d["department_id"],
                    "department_name": d["department_name"],
                    "shift": shift,
                    "nurses_on_duty": nurses,
                })
                staff_id += 1
    return pd.DataFrame(rows)


def generate_admissions(dept_df: pd.DataFrame) -> pd.DataFrame:
    """Patient admission records (the Hospital Beds Management style fact)."""
    rows = []
    adm_id = 1
    for day in range(N_DAYS):
        dt = START_DATE + timedelta(days=day)
        season = _seasonal_multiplier(day)
        wk = _weekday_multiplier(dt)
        # Injected admission surge anomalies on specific days
        surge = 1.5 if day in (37, 92, 150) else 1.0
        for _, d in dept_df.iterrows():
            lam = d["adm_per_day"] * season * wk * surge
            n_adm = np.random.poisson(max(0.3, lam))
            for _ in range(n_adm):
                shift = random.choices(SHIFTS, weights=[0.42, 0.36, 0.22])[0]
                h0, h1 = SHIFT_HOURS[shift]
                hour = random.randint(h0, h1 - 1) % 24
                admit_time = dt + timedelta(hours=hour, minutes=random.randint(0, 59))
                is_emerg = random.random() < d["emergency_share"]
                adm_type = "Emergency" if is_emerg else "Elective"
                urgency = (
                    random.choices(URGENCY_LEVELS, weights=[0.25, 0.4, 0.25, 0.1])[0]
                    if is_emerg else
                    random.choices(URGENCY_LEVELS, weights=[0.02, 0.15, 0.45, 0.38])[0]
                )
                # Log-normal LOS: mean ~= avg_los, moderate tail (no runaway outliers)
                mean_los = float(d["avg_length_of_stay"])
                sigma = 0.5
                mu = np.log(mean_los) - 0.5 * sigma ** 2
                los_days = float(np.clip(np.random.lognormal(mu, sigma), 0.2, mean_los * 3.5))
                discharge_time = admit_time + timedelta(days=float(los_days))
                age = int(np.clip(np.random.normal(48, 20), 0, 98))
                rows.append({
                    "admission_id": adm_id,
                    "patient_id": f"P{random.randint(100000, 999999)}",
                    "department_id": d["department_id"],
                    "department_name": d["department_name"],
                    "admit_time": admit_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "discharge_time": discharge_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "admit_date": admit_time.strftime("%Y-%m-%d"),
                    "shift": shift,
                    "admission_type": adm_type,
                    "urgency": urgency,
                    "length_of_stay_days": round(float(los_days), 2),
                    "patient_age": age,
                    "transferred": random.random() < 0.08,
                })
                adm_id += 1
    return pd.DataFrame(rows)


def generate_er_visits(dept_df: pd.DataFrame, staff_df: pd.DataFrame) -> pd.DataFrame:
    """ER Wait Time style dataset: wait time driven by occupancy, urgency, nurse ratio."""
    emerg = dept_df[dept_df["department_name"] == "Emergency"].iloc[0]
    staff_lookup = {
        (r["date"], r["shift"]): r["nurses_on_duty"]
        for _, r in staff_df[staff_df["department_name"] == "Emergency"].iterrows()
    }
    rows = []
    vid = 1
    for day in range(N_DAYS):
        dt = START_DATE + timedelta(days=day)
        season = _seasonal_multiplier(day)
        wk = _weekday_multiplier(dt)
        daily_visits = int(np.random.poisson(55 * season * wk))
        for _ in range(daily_visits):
            shift = random.choices(SHIFTS, weights=[0.40, 0.37, 0.23])[0]
            h0, h1 = SHIFT_HOURS[shift]
            hour = random.randint(h0, h1 - 1) % 24
            arrival = dt + timedelta(hours=hour, minutes=random.randint(0, 59))
            urgency = random.choices(URGENCY_LEVELS, weights=URGENCY_WEIGHTS)[0]
            nurses = staff_lookup.get((dt.strftime("%Y-%m-%d"), shift), 4)
            # synthetic current occupancy of ER around this time
            occupancy = float(np.clip(np.random.normal(0.78, 0.14), 0.3, 1.05))
            patients_in_queue = int(max(0, np.random.poisson(8 * occupancy)))
            nurse_ratio = round(patients_in_queue / max(1, nurses) + np.random.normal(0, 0.4), 2)
            nurse_ratio = max(0.5, nurse_ratio)
            urgency_factor = {"Critical": 0.3, "High": 0.6, "Medium": 1.0, "Low": 1.4}[urgency]
            # base wait grows with occupancy and nurse ratio, shrinks with urgency priority
            base_wait = (
                12
                + 55 * (occupancy ** 2)
                + 6.5 * nurse_ratio
                + (9 if shift == "Night" else 0)
            ) * urgency_factor
            wait = max(2.0, np.random.normal(base_wait, base_wait * 0.18))
            rows.append({
                "visit_id": vid,
                "arrival_time": arrival.strftime("%Y-%m-%d %H:%M:%S"),
                "arrival_date": arrival.strftime("%Y-%m-%d"),
                "shift": shift,
                "urgency": urgency,
                "er_occupancy": round(occupancy, 3),
                "patients_in_queue": patients_in_queue,
                "nurses_on_duty": nurses,
                "nurse_patient_ratio": nurse_ratio,
                "wait_time_min": round(float(wait), 1),
                "facility_size": "Large",
            })
            vid += 1
    return pd.DataFrame(rows)


def generate_all(out_dir: Path | None = None) -> dict[str, Path]:
    out_dir = out_dir or (RAW_DIR / "synthetic")
    out_dir.mkdir(parents=True, exist_ok=True)

    dept = generate_departments()
    staff = generate_staffing(dept)
    adm = generate_admissions(dept)
    er = generate_er_visits(dept, staff)

    paths = {}
    for name, df in [
        ("departments", dept),
        ("staffing", staff),
        ("admissions", adm),
        ("er_visits", er),
    ]:
        p = out_dir / f"{name}.csv"
        df.to_csv(p, index=False)
        paths[name] = p
    return paths


if __name__ == "__main__":
    paths = generate_all()
    for name, p in paths.items():
        df = pd.read_csv(p)
        print(f"{name:14s} -> {p}  ({len(df):,} rows, {len(df.columns)} cols)")
