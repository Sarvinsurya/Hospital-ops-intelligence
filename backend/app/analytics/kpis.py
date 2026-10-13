"""
Analytics layer — all operational KPIs required by the project abstract.

KPIs implemented:
  * Bed Occupancy Rate (overall + per department, with trend)
  * Daily / Weekly Admission Volume
  * Average Patient Waiting Time (overall, by urgency, by shift)
  * Department Workload Index (composite stress score)
  * Patient Flow (arrivals, transfers, discharges)
  * Emergency vs Elective admission split
  * Average Length of Stay (ALOS) by department
  * Nurse-to-patient ratio / staffing efficiency analysis
Each function returns plain Python dict/list structures ready for JSON APIs.
"""
from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from app.core.config import settings
from app.core.database import query_df


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _latest_date() -> str:
    """The latest fully-populated operational day (has both admissions & staffing).

    Note: fact_bed_occupancy_daily extends past the last admission day because
    discharge intervals run forward in time, so we anchor on admissions instead.
    """
    df = query_df("SELECT MAX(admit_date) AS d FROM fact_admissions")
    return df.iloc[0]["d"]


def _status_for_occupancy(rate: float) -> str:
    if rate >= settings.occupancy_critical:
        return "critical"
    if rate >= settings.occupancy_warning:
        return "warning"
    return "normal"


def _status_for_wait(mins: float) -> str:
    if mins >= settings.wait_time_critical_min:
        return "critical"
    if mins >= settings.wait_time_warning_min:
        return "warning"
    return "normal"


# ---------------------------------------------------------------------------
# Bed occupancy
# ---------------------------------------------------------------------------
def bed_occupancy_overall() -> dict:
    latest = _latest_date()
    df = query_df(
        "SELECT SUM(beds_occupied) occ, SUM(total_beds) total "
        "FROM fact_bed_occupancy_daily WHERE date = ?",
        (latest,),
    )
    occ, total = int(df.iloc[0]["occ"]), int(df.iloc[0]["total"])
    rate = occ / total if total else 0.0
    return {
        "date": latest,
        "beds_occupied": occ,
        "total_beds": total,
        "available_beds": total - occ,
        "occupancy_rate": round(rate, 4),
        "status": _status_for_occupancy(rate),
    }


def bed_occupancy_by_department() -> list[dict]:
    latest = _latest_date()
    df = query_df(
        """
        SELECT d.department_id, d.department_name,
               o.beds_occupied, o.total_beds, o.occupancy_rate
        FROM fact_bed_occupancy_daily o
        JOIN dim_department d ON o.department_id = d.department_id
        WHERE o.date = ?
        ORDER BY o.occupancy_rate DESC
        """,
        (latest,),
    )
    out = []
    for _, r in df.iterrows():
        out.append({
            "department_id": int(r["department_id"]),
            "department_name": r["department_name"],
            "beds_occupied": int(r["beds_occupied"]),
            "total_beds": int(r["total_beds"]),
            "available_beds": int(r["total_beds"] - r["beds_occupied"]),
            "occupancy_rate": round(float(r["occupancy_rate"]), 4),
            "status": _status_for_occupancy(float(r["occupancy_rate"])),
        })
    return out


def occupancy_trend(days: int = 30) -> list[dict]:
    df = query_df(
        """
        SELECT date,
               ROUND(CAST(SUM(beds_occupied) AS FLOAT) / SUM(total_beds), 4) AS occupancy_rate
        FROM fact_bed_occupancy_daily
        GROUP BY date ORDER BY date DESC LIMIT ?
        """,
        (days,),
    )
    df = df.iloc[::-1]  # chronological
    return [{"date": r["date"], "occupancy_rate": float(r["occupancy_rate"])} for _, r in df.iterrows()]


# ---------------------------------------------------------------------------
# Admissions volume
# ---------------------------------------------------------------------------
def admission_volume_daily(days: int = 30) -> list[dict]:
    df = query_df(
        """
        SELECT admit_date AS date, COUNT(*) AS admissions
        FROM fact_admissions GROUP BY admit_date
        ORDER BY admit_date DESC LIMIT ?
        """,
        (days,),
    )
    df = df.iloc[::-1]
    return [{"date": r["date"], "admissions": int(r["admissions"])} for _, r in df.iterrows()]


def admission_volume_weekly() -> list[dict]:
    df = query_df(
        """
        SELECT dd.year, dd.week, COUNT(*) AS admissions
        FROM fact_admissions fa
        JOIN dim_date dd ON fa.admit_date = dd.date
        GROUP BY dd.year, dd.week ORDER BY dd.year, dd.week
        """
    )
    return [
        {"period": f"{int(r['year'])}-W{int(r['week']):02d}", "admissions": int(r["admissions"])}
        for _, r in df.iterrows()
    ]


# ---------------------------------------------------------------------------
# Waiting time
# ---------------------------------------------------------------------------
def waiting_time_summary() -> dict:
    df = query_df("SELECT AVG(wait_time_min) avg, "
                  "MAX(wait_time_min) max, MIN(wait_time_min) min FROM fact_er_visits")
    avg = float(df.iloc[0]["avg"])
    return {
        "avg_wait_min": round(avg, 1),
        "max_wait_min": round(float(df.iloc[0]["max"]), 1),
        "min_wait_min": round(float(df.iloc[0]["min"]), 1),
        "status": _status_for_wait(avg),
    }


def waiting_time_by_urgency() -> list[dict]:
    df = query_df(
        "SELECT urgency, ROUND(AVG(wait_time_min),1) avg_wait, COUNT(*) n "
        "FROM fact_er_visits GROUP BY urgency"
    )
    order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    rows = [
        {"urgency": r["urgency"], "avg_wait_min": float(r["avg_wait"]), "visits": int(r["n"])}
        for _, r in df.iterrows()
    ]
    return sorted(rows, key=lambda x: order.get(x["urgency"], 9))


def waiting_time_by_shift() -> list[dict]:
    df = query_df(
        "SELECT shift, ROUND(AVG(wait_time_min),1) avg_wait, COUNT(*) n "
        "FROM fact_er_visits GROUP BY shift"
    )
    order = {"Morning": 0, "Evening": 1, "Night": 2}
    rows = [
        {"shift": r["shift"], "avg_wait_min": float(r["avg_wait"]), "visits": int(r["n"])}
        for _, r in df.iterrows()
    ]
    return sorted(rows, key=lambda x: order.get(x["shift"], 9))


# ---------------------------------------------------------------------------
# Department workload index (composite stress score 0-100)
# ---------------------------------------------------------------------------
def department_workload_index() -> list[dict]:
    latest = _latest_date()
    occ = query_df(
        "SELECT department_id, occupancy_rate FROM fact_bed_occupancy_daily WHERE date = ?",
        (latest,),
    )
    adm = query_df(
        "SELECT department_id, COUNT(*) n FROM fact_admissions WHERE admit_date = ? GROUP BY department_id",
        (latest,),
    )
    staff = query_df(
        "SELECT department_id, AVG(nurses_on_duty) nurses FROM fact_staffing WHERE date = ? GROUP BY department_id",
        (latest,),
    )
    dept = query_df("SELECT department_id, department_name, total_beds FROM dim_department")

    m = dept.merge(occ, on="department_id", how="left") \
            .merge(adm, on="department_id", how="left") \
            .merge(staff, on="department_id", how="left")
    m["occupancy_rate"] = m["occupancy_rate"].fillna(0.0).astype(float)
    m["n"] = m["n"].fillna(0).astype(float)
    m["nurses"] = m["nurses"].fillna(0).astype(float)

    # normalize components
    adm_norm = m["n"] / (m["n"].max() or 1)
    patients_per_nurse = m["occupancy_rate"] * m["total_beds"] / m["nurses"].replace(0, np.nan)
    patients_per_nurse = patients_per_nurse.fillna(patients_per_nurse.max()).fillna(0)
    ppn_norm = patients_per_nurse / (patients_per_nurse.max() or 1)

    # weighted composite: occupancy 50%, admissions pressure 25%, nurse load 25%
    workload = (0.5 * m["occupancy_rate"] + 0.25 * adm_norm + 0.25 * ppn_norm) * 100

    out = []
    for i, r in m.iterrows():
        score = round(float(workload.iloc[i]), 1)
        out.append({
            "department_id": int(r["department_id"]),
            "department_name": r["department_name"],
            "workload_index": score,
            "occupancy_rate": round(float(r["occupancy_rate"]), 4),
            "admissions_today": int(r["n"]),
            "avg_nurses": round(float(r["nurses"]), 1),
            "patients_per_nurse": round(float(patients_per_nurse.iloc[i]), 1),
            "status": "critical" if score >= 85 else "warning" if score >= 70 else "normal",
        })
    return sorted(out, key=lambda x: x["workload_index"], reverse=True)


# ---------------------------------------------------------------------------
# Patient flow (arrivals / transfers / discharges)
# ---------------------------------------------------------------------------
def patient_flow(days: int = 14) -> list[dict]:
    arrivals = query_df(
        "SELECT admit_date d, COUNT(*) n FROM fact_admissions GROUP BY admit_date ORDER BY admit_date DESC LIMIT ?",
        (days,),
    )
    transfers = query_df(
        "SELECT admit_date d, SUM(transferred) n FROM fact_admissions GROUP BY admit_date ORDER BY admit_date DESC LIMIT ?",
        (days,),
    )
    discharges = query_df(
        "SELECT DATE(discharge_time) d, COUNT(*) n FROM fact_admissions GROUP BY DATE(discharge_time)",
    )
    disc_map = dict(zip(discharges["d"], discharges["n"]))
    tr_map = dict(zip(transfers["d"], transfers["n"]))

    out = []
    for _, r in arrivals.iloc[::-1].iterrows():
        d = r["d"]
        out.append({
            "date": d,
            "arrivals": int(r["n"]),
            "transfers": int(tr_map.get(d, 0) or 0),
            "discharges": int(disc_map.get(d, 0) or 0),
        })
    return out


def patient_flow_sankey() -> dict:
    """Nodes/links for a Sankey: Arrivals -> Departments -> (Transfer | Discharge)."""
    dept = query_df(
        "SELECT department_name, COUNT(*) n, SUM(transferred) tr FROM fact_admissions GROUP BY department_name"
    )
    nodes = [{"name": "Arrivals"}]
    nodes += [{"name": r["department_name"]} for _, r in dept.iterrows()]
    nodes += [{"name": "Transferred"}, {"name": "Discharged"}]
    links = []
    for _, r in dept.iterrows():
        n = int(r["n"])
        tr = int(r["tr"] or 0)
        links.append({"source": "Arrivals", "target": r["department_name"], "value": n})
        links.append({"source": r["department_name"], "target": "Transferred", "value": tr})
        links.append({"source": r["department_name"], "target": "Discharged", "value": n - tr})
    return {"nodes": nodes, "links": links}


# ---------------------------------------------------------------------------
# Emergency vs elective
# ---------------------------------------------------------------------------
def emergency_vs_elective() -> list[dict]:
    df = query_df(
        "SELECT admission_type, COUNT(*) n FROM fact_admissions GROUP BY admission_type"
    )
    total = df["n"].sum()
    return [
        {"type": r["admission_type"], "count": int(r["n"]), "share": round(float(r["n"]) / float(total), 4)}
        for _, r in df.iterrows()
    ]


# ---------------------------------------------------------------------------
# ALOS
# ---------------------------------------------------------------------------
def alos_by_department() -> list[dict]:
    df = query_df(
        """
        SELECT d.department_name, ROUND(AVG(fa.length_of_stay_days),2) alos, COUNT(*) n
        FROM fact_admissions fa JOIN dim_department d ON fa.department_id = d.department_id
        GROUP BY d.department_name ORDER BY alos DESC
        """
    )
    return [
        {"department_name": r["department_name"], "alos_days": float(r["alos"]), "admissions": int(r["n"])}
        for _, r in df.iterrows()
    ]


# ---------------------------------------------------------------------------
# Staffing efficiency / nurse-patient ratio analysis
# ---------------------------------------------------------------------------
def staffing_efficiency() -> list[dict]:
    """Nurse:patient ratio by department x shift with wait-time correlation signal."""
    latest = _latest_date()
    staff = query_df(
        """
        SELECT s.department_id, d.department_name, s.shift, AVG(s.nurses_on_duty) nurses
        FROM fact_staffing s JOIN dim_department d ON s.department_id = d.department_id
        WHERE s.date = ? GROUP BY s.department_id, s.shift
        """,
        (latest,),
    )
    occ = query_df(
        "SELECT department_id, beds_occupied FROM fact_bed_occupancy_daily WHERE date = ?",
        (latest,),
    )
    occ_map = dict(zip(occ["department_id"], occ["beds_occupied"]))
    out = []
    for _, r in staff.iterrows():
        occupied = occ_map.get(r["department_id"], 0)
        # distribute occupied beds across 3 shifts as present patients
        ppn = occupied / max(1, r["nurses"])
        out.append({
            "department_id": int(r["department_id"]),
            "department_name": r["department_name"],
            "shift": r["shift"],
            "nurses_on_duty": round(float(r["nurses"]), 1),
            "patients_per_nurse": round(float(ppn), 1),
            "status": "danger" if ppn >= settings.nurse_ratio_danger else "ok",
        })
    return out


# ---------------------------------------------------------------------------
# One-shot dashboard summary
# ---------------------------------------------------------------------------
def dashboard_summary() -> dict:
    occ = bed_occupancy_overall()
    wait = waiting_time_summary()
    adm_today = query_df(
        "SELECT COUNT(*) n FROM fact_admissions WHERE admit_date = ?",
        (_latest_date(),),
    ).iloc[0]["n"]
    ee = emergency_vs_elective()
    emerg = next((x["share"] for x in ee if x["type"] == "Emergency"), 0)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "occupancy": occ,
        "waiting_time": wait,
        "admissions_today": int(adm_today),
        "emergency_share": round(float(emerg), 4),
    }
