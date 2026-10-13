"""
Bed-availability window estimation.

Projects near-term bed availability per department so staff can act BEFORE a
shortage occurs (proactive, as the abstract requires). Combines:
  * current occupancy census
  * expected discharges over the next N days (from in-house patients' discharge_time)
  * forecasted new admissions (from the forecasting model)

Produces, per department, the projected free beds per day and the first day a
shortage (occupancy >= critical threshold) is expected — the "availability window".
"""
from __future__ import annotations

import pandas as pd

from app.core.config import settings
from app.core.database import query_df
from app.ml.forecasting import forecast_admissions


def _latest_date() -> str:
    return query_df("SELECT MAX(admit_date) d FROM fact_admissions").iloc[0]["d"]


def bed_availability_forecast(department_id: int, horizon_days: int = 5) -> dict:
    latest = pd.to_datetime(_latest_date())
    dept = query_df(
        "SELECT department_name, total_beds FROM dim_department WHERE department_id = ?",
        (department_id,),
    ).iloc[0]
    total_beds = int(dept["total_beds"])

    # current census at latest date (noon)
    occ_now = query_df(
        "SELECT beds_occupied FROM fact_bed_occupancy_daily WHERE department_id = ? AND date = ?",
        (department_id, latest.strftime("%Y-%m-%d")),
    )
    occupied = int(occ_now.iloc[0]["beds_occupied"]) if not occ_now.empty else 0

    # expected discharges per upcoming day from currently-admitted patients
    inhouse = query_df(
        """
        SELECT discharge_time FROM fact_admissions
        WHERE department_id = ? AND admit_time <= ? AND discharge_time > ?
        """,
        (department_id, latest.strftime("%Y-%m-%d 12:00:00"), latest.strftime("%Y-%m-%d 12:00:00")),
    )
    disc = pd.to_datetime(inhouse["discharge_time"])

    # forecasted new admissions for the department
    fc = forecast_admissions(department_id, horizon=horizon_days)["forecast"]

    projection = []
    running = occupied
    shortage_day = None
    for i in range(1, horizon_days + 1):
        day = latest + pd.Timedelta(days=i)
        day_noon = day + pd.Timedelta(hours=12)
        discharges_today = int((disc <= day_noon).sum()) - int((disc <= (day_noon - pd.Timedelta(days=1))).sum())
        discharges_today = max(0, discharges_today)
        new_adm = fc[i - 1]["predicted_admissions"]
        running = max(0, min(total_beds, running - discharges_today + new_adm))
        rate = running / total_beds if total_beds else 0.0
        if shortage_day is None and rate >= settings.occupancy_critical:
            shortage_day = day.strftime("%Y-%m-%d")
        projection.append({
            "date": day.strftime("%Y-%m-%d"),
            "projected_occupied": round(running, 1),
            "projected_free": round(total_beds - running, 1),
            "projected_occupancy_rate": round(rate, 3),
            "expected_discharges": discharges_today,
            "expected_admissions": new_adm,
            "status": "critical" if rate >= settings.occupancy_critical
                      else "warning" if rate >= settings.occupancy_warning else "normal",
        })

    return {
        "department_id": department_id,
        "department_name": dept["department_name"],
        "total_beds": total_beds,
        "current_occupied": occupied,
        "current_free": total_beds - occupied,
        "shortage_expected_on": shortage_day,
        "projection": projection,
    }


def all_departments_availability(horizon_days: int = 5) -> list[dict]:
    depts = query_df("SELECT department_id FROM dim_department ORDER BY department_id")
    return [bed_availability_forecast(int(r["department_id"]), horizon_days) for _, r in depts.iterrows()]
