"""
ETL: build the SQLite warehouse for the Hospital Operations Intelligence System.

Pipeline (as per abstract):  Data -> ETL -> Warehouse (SQLite) -> Analytics/ML/Agent

Source priority:
  1. Real Kaggle CSVs if present in data/raw/ (hospital-beds-management, er-wait-time)
  2. Synthetic generator fallback (always available) in data/raw/synthetic/

Warehouse schema (star-ish):
  dim_department   (department_id, department_name, total_beds, ...)
  dim_date         (date, year, month, day, weekday, is_weekend)
  fact_admissions  (admission grain)
  fact_er_visits   (ER visit grain, wait times)
  fact_staffing    (dept x shift x day nurse roster)
  fact_bed_occupancy_daily (derived: beds occupied per dept per day)
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from app.core.config import RAW_DIR
from app.core.database import get_connection
from app.etl import generate_synthetic
from app.etl import load_real


def _load_sources() -> dict[str, pd.DataFrame]:
    """Load synthetic CSVs, generating them first if missing."""
    syn = RAW_DIR / "synthetic"
    needed = ["departments", "staffing", "admissions", "er_visits"]
    if not all((syn / f"{n}.csv").exists() for n in needed):
        generate_synthetic.generate_all()
    return {n: pd.read_csv(syn / f"{n}.csv") for n in needed}


def _build_dim_date(adm: pd.DataFrame, er: pd.DataFrame) -> pd.DataFrame:
    dates = pd.to_datetime(
        pd.concat([adm["admit_date"], er["arrival_date"]]).unique()
    )
    df = pd.DataFrame({"date": sorted(dates)})
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    d = pd.to_datetime(df["date"])
    df["year"] = d.dt.year
    df["month"] = d.dt.month
    df["day"] = d.dt.day
    df["weekday"] = d.dt.day_name()
    df["week"] = d.dt.isocalendar().week.astype(int)
    df["is_weekend"] = (d.dt.weekday >= 5).astype(int)
    return df


def _build_bed_occupancy(adm: pd.DataFrame, dept: pd.DataFrame) -> pd.DataFrame:
    """Derive daily beds-occupied per department as a point-in-time census.

    Bed occupancy is a census, not an "any overlap" measure: we count patients
    physically in a bed at the midday snapshot (12:00) of each day. A patient is
    counted if admit_time <= noon < discharge_time. This matches how hospitals
    report occupancy and keeps the rate aligned with arrival_rate * mean_LOS.
    """
    adm = adm.copy()
    adm["admit_time"] = pd.to_datetime(adm["admit_time"])
    adm["discharge_time"] = pd.to_datetime(adm["discharge_time"])

    start = adm["admit_time"].min().normalize()
    end = adm["admit_time"].max().normalize()
    days = pd.date_range(start, end, freq="D")
    beds_map = dict(zip(dept["department_id"], dept["total_beds"]))

    rows = []
    for dep_id, g in adm.groupby("department_id"):
        total = beds_map.get(dep_id, 1)
        a = g["admit_time"].values.astype("datetime64[ns]")
        dis = g["discharge_time"].values.astype("datetime64[ns]")
        for day in days:
            noon = (day + timedelta(hours=12)).to_datetime64()
            occupied = int(((a <= noon) & (dis > noon)).sum())
            occupied = min(occupied, total)
            rows.append({
                "date": day.strftime("%Y-%m-%d"),
                "department_id": int(dep_id),
                "beds_occupied": occupied,
                "total_beds": int(total),
                "occupancy_rate": round(occupied / total, 4) if total else 0.0,
            })
    return pd.DataFrame(rows)


def _align_er_dates(er: pd.DataFrame, target_end: str) -> pd.DataFrame:
    """Shift real ER arrival dates forward so the series ENDS at target_end.

    The real ER values (urgency, wait times, nurse ratios, outcomes) are untouched —
    only the calendar is translated so the real ER data overlaps the operational
    dashboard window ('now'). This keeps the data genuinely real while letting the
    daily control room and the ER analytics share one timeline.
    """
    er = er.copy()
    at = pd.to_datetime(er["arrival_time"])
    delta = pd.to_datetime(target_end) - at.max().normalize()
    at = at + delta
    er["arrival_time"] = at.dt.strftime("%Y-%m-%d %H:%M:%S")
    er["arrival_date"] = at.dt.strftime("%Y-%m-%d")
    return er


def build_warehouse() -> dict[str, int]:
    src = _load_sources()
    dept, staff, adm = src["departments"], src["staffing"], src["admissions"]

    # ---- ER visits: prefer the REAL Kaggle dataset (Option B) ----
    real_tables: dict[str, pd.DataFrame] = {}
    if load_real.real_data_available():
        er = load_real.load_real_er_visits()
        er = _align_er_dates(er, target_end=adm["admit_date"].max())
        real_tables["fact_services_weekly"] = load_real.load_real_services_weekly()
        real_tables["fact_patients_real"] = load_real.load_real_patients()
        real_tables["fact_staff_schedule_real"] = load_real.load_real_staff_schedule()
        data_source = "real_er + synthetic_ops"
    else:
        er = src["er_visits"]
        data_source = "synthetic"

    dim_date = _build_dim_date(adm, er)
    bed_occ = _build_bed_occupancy(adm, dept)

    tables = {
        "dim_department": dept,
        "dim_date": dim_date,
        "fact_admissions": adm,
        "fact_er_visits": er,
        "fact_staffing": staff,
        "fact_bed_occupancy_daily": bed_occ,
        **real_tables,
    }
    print(f"[ETL] data source: {data_source}")

    conn = get_connection()
    counts = {}
    try:
        for name, df in tables.items():
            df.to_sql(name, conn, if_exists="replace", index=False)
            counts[name] = len(df)
        # Helpful indexes
        cur = conn.cursor()
        cur.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_adm_dept ON fact_admissions(department_id);
            CREATE INDEX IF NOT EXISTS idx_adm_date ON fact_admissions(admit_date);
            CREATE INDEX IF NOT EXISTS idx_er_date ON fact_er_visits(arrival_date);
            CREATE INDEX IF NOT EXISTS idx_occ_date ON fact_bed_occupancy_daily(date);
            CREATE INDEX IF NOT EXISTS idx_staff_date ON fact_staffing(date);
            """
        )
        conn.commit()
    finally:
        conn.close()
    return counts


if __name__ == "__main__":
    counts = build_warehouse()
    print("Warehouse built:")
    for t, n in counts.items():
        print(f"  {t:28s} {n:,} rows")
