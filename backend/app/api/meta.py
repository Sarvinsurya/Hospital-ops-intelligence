"""Reference / metadata endpoints: departments, data-source provenance."""
from fastapi import APIRouter

from app.core.database import query_df
from app.etl import load_real

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/departments")
def departments():
    df = query_df("SELECT * FROM dim_department ORDER BY department_id")
    return df.to_dict("records")


@router.get("/data-source")
def data_source():
    """Provenance: which tables come from REAL Kaggle data vs synthetic backbone."""
    real = load_real.real_data_available()
    counts = {}
    for t in ["fact_admissions", "fact_er_visits", "fact_services_weekly",
              "fact_patients_real", "fact_staff_schedule_real"]:
        try:
            counts[t] = int(query_df(f"SELECT COUNT(*) n FROM {t}").iloc[0]["n"])
        except Exception:
            counts[t] = 0
    return {
        "real_data_available": real,
        "sources": {
            "ER Wait Time (Kaggle, real)": "fact_er_visits",
            "Hospital Beds Management (Kaggle, real)": ["fact_services_weekly", "fact_patients_real", "fact_staff_schedule_real"],
            "Operational backbone (synthetic, calibrated to real)": ["fact_admissions", "fact_staffing", "fact_bed_occupancy_daily"],
        },
        "row_counts": counts,
    }


@router.get("/services-weekly")
def services_weekly():
    df = query_df("SELECT * FROM fact_services_weekly ORDER BY week, service")
    return df.to_dict("records")
