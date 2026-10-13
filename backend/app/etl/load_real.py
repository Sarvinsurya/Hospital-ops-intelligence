"""
Load and normalize the REAL Kaggle datasets into warehouse-compatible frames.

Datasets (placed under data/raw/):
  hospital_beds/services_weekly.csv   weekly per-service beds/admissions
  hospital_beds/patients.csv          1000 patient stays (ALOS source)
  hospital_beds/staff_schedule.csv    weekly staff presence
  hospital_beds/staff.csv             staff roster
  er_wait/er_wait_time.csv            5000 ER visits (the wait-time ground truth)

Option B strategy:
  * The REAL ER dataset becomes fact_er_visits (drives waiting-time KPIs + ML).
  * The REAL beds data becomes reference tables (fact_services_weekly, fact_patients_real)
    surfaced in a "Source Data" view so the Kaggle beds data is demonstrably used.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.core.config import RAW_DIR

BEDS_DIR = RAW_DIR / "hospital_beds"
ER_DIR = RAW_DIR / "er_wait"

# Map the ER dataset's coarse "Time of Day" to our Morning/Evening/Night shifts
_TIME_OF_DAY_TO_SHIFT = {
    "Early Morning": "Morning",
    "Late Morning": "Morning",
    "Afternoon": "Evening",
    "Evening": "Evening",
    "Night": "Night",
}


def real_data_available() -> bool:
    return (ER_DIR / "er_wait_time.csv").exists()


def load_real_er_visits() -> pd.DataFrame:
    """Normalize the real ER Wait Time dataset into the fact_er_visits schema."""
    df = pd.read_csv(ER_DIR / "er_wait_time.csv")
    out = pd.DataFrame()
    out["visit_id"] = range(1, len(df) + 1)
    arrival = pd.to_datetime(df["Visit Date"])
    out["arrival_time"] = arrival.dt.strftime("%Y-%m-%d %H:%M:%S")
    out["arrival_date"] = arrival.dt.strftime("%Y-%m-%d")
    out["shift"] = df["Time of Day"].map(_TIME_OF_DAY_TO_SHIFT).fillna("Morning")
    out["urgency"] = df["Urgency Level"]
    # Nurse-to-Patient Ratio in the dataset is "N patients per nurse" (1..5)
    out["nurse_patient_ratio"] = df["Nurse-to-Patient Ratio"].astype(float)
    # Derive an occupancy proxy from nurse ratio (higher ratio -> busier)
    out["er_occupancy"] = (df["Nurse-to-Patient Ratio"] / 5.0).clip(0.2, 1.0).round(3)
    out["patients_in_queue"] = (df["Nurse-to-Patient Ratio"] * 2).astype(int)
    out["nurses_on_duty"] = (df["Facility Size (Beds)"] / 20).round().clip(lower=1).astype(int)
    out["wait_time_min"] = df["Total Wait Time (min)"].astype(float)
    out["facility_size"] = df["Facility Size (Beds)"].apply(
        lambda b: "Large" if b >= 100 else "Medium" if b >= 50 else "Small"
    )
    # Extra real fields preserved for richer analytics
    out["region"] = df["Region"]
    out["hospital_name"] = df["Hospital Name"]
    out["season"] = df["Season"]
    out["day_of_week"] = df["Day of Week"]
    out["specialist_availability"] = df["Specialist Availability"]
    out["time_to_registration_min"] = df["Time to Registration (min)"]
    out["time_to_triage_min"] = df["Time to Triage (min)"]
    out["time_to_professional_min"] = df["Time to Medical Professional (min)"]
    out["patient_outcome"] = df["Patient Outcome"]
    out["patient_satisfaction"] = df["Patient Satisfaction"]
    return out


def load_real_services_weekly() -> pd.DataFrame:
    df = pd.read_csv(BEDS_DIR / "services_weekly.csv")
    df["occupancy_rate"] = (df["patients_admitted"] / df["available_beds"]).round(4)
    return df


def load_real_patients() -> pd.DataFrame:
    df = pd.read_csv(BEDS_DIR / "patients.csv")
    arr = pd.to_datetime(df["arrival_date"])
    dep = pd.to_datetime(df["departure_date"])
    df["length_of_stay_days"] = (dep - arr).dt.days.clip(lower=0)
    return df


def load_real_staff_schedule() -> pd.DataFrame:
    return pd.read_csv(BEDS_DIR / "staff_schedule.csv")
