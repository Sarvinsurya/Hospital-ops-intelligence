"""
Agent tool suite — hospital-operations investigation tools.

Each tool is a plain Python function returning JSON-serializable data, plus an
Ollama tool schema describing it. The agent (qwen2.5:3b) selects and calls these
to gather evidence before producing an evidence-based recommendation.

Tools map directly onto the abstract's Agent Function requirements:
  * query current occupancy / workload / staffing   -> root-cause investigation
  * forecast volume / predict wait / bed availability-> proactive reasoning
  * reallocation simulator                           -> actionable recommendations
  * raw SQL (read-only)                              -> any ad-hoc evidence
"""
from __future__ import annotations

import re

from app.analytics import kpis
from app.core.database import query_df
from app.ml import forecasting, wait_time, bed_availability, anomaly


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------
def get_occupancy_overview() -> dict:
    """Current overall + per-department bed occupancy."""
    return {
        "overall": kpis.bed_occupancy_overall(),
        "by_department": kpis.bed_occupancy_by_department(),
    }


def get_department_workload() -> list[dict]:
    """Composite workload stress index per department (0-100)."""
    return kpis.department_workload_index()


def get_waiting_times() -> dict:
    """ER waiting time summary, by urgency and by shift."""
    return {
        "summary": kpis.waiting_time_summary(),
        "by_urgency": kpis.waiting_time_by_urgency(),
        "by_shift": kpis.waiting_time_by_shift(),
    }


def get_staffing_status() -> list[dict]:
    """Nurse-to-patient ratio per department x shift, flagging danger zones."""
    return kpis.staffing_efficiency()


def get_anomalies() -> dict:
    """All current operational anomalies (occupancy, staffing, spikes, waits)."""
    return anomaly.detect_all()


def forecast_admissions_tool(department_id: int | None = None, horizon: int = 7) -> dict:
    """Forecast daily admission volume (optionally for one department)."""
    return forecasting.forecast_admissions(department_id, horizon)


def predict_wait_time_tool(urgency: str, nurse_patient_ratio: float, er_occupancy: float,
                           shift: str = "Morning", specialist_availability: int = 3) -> dict:
    """Predict ER wait time for a scenario (uses the real-data ML model)."""
    return wait_time.predict(urgency, nurse_patient_ratio, er_occupancy, shift, specialist_availability)


def get_bed_availability(department_id: int, horizon_days: int = 5) -> dict:
    """Project bed availability window for a department (when a shortage is expected)."""
    return bed_availability.bed_availability_forecast(department_id, horizon_days)


def simulate_reallocation(from_department: str, to_department: str, patients: int) -> dict:
    """Simulate moving `patients` beds from one department to another and show the
    projected occupancy of both AFTER the move. Core of the recommendation engine."""
    occ = {d["department_name"]: d for d in kpis.bed_occupancy_by_department()}
    if from_department not in occ or to_department not in occ:
        return {"error": f"Unknown department. Valid: {list(occ.keys())}"}
    src, dst = occ[from_department], occ[to_department]

    new_src_occ = max(0, src["beds_occupied"] - patients)
    new_dst_occ = min(dst["total_beds"], dst["beds_occupied"] + patients)
    moved = dst["beds_occupied"] + patients - new_dst_occ  # capped if dst fills
    feasible = (dst["available_beds"] >= patients) and (src["beds_occupied"] >= patients)
    return {
        "from": {
            "department": from_department,
            "before_rate": src["occupancy_rate"],
            "after_rate": round(new_src_occ / src["total_beds"], 3),
        },
        "to": {
            "department": to_department,
            "before_rate": dst["occupancy_rate"],
            "after_rate": round(new_dst_occ / dst["total_beds"], 3),
            "spare_capacity": dst["available_beds"],
        },
        "patients_requested": patients,
        "feasible": bool(feasible),
        "note": "feasible" if feasible else "destination lacks enough free beds for all patients",
    }


_SQL_FORBIDDEN = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|PRAGMA)\b", re.I)


def execute_sql(query: str) -> dict:
    """Run a READ-ONLY SQL query against the warehouse for ad-hoc evidence.
    Tables: dim_department, dim_date, fact_admissions, fact_er_visits,
    fact_staffing, fact_bed_occupancy_daily, fact_services_weekly, fact_patients_real."""
    if _SQL_FORBIDDEN.search(query) or ";" in query.strip().rstrip(";"):
        return {"error": "Only single read-only SELECT statements are allowed."}
    if not query.strip().lower().startswith("select"):
        return {"error": "Query must start with SELECT."}
    try:
        df = query_df(query)
        return {"rows": df.head(50).to_dict("records"), "row_count": int(len(df))}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Dispatch table + Ollama tool schemas
# ---------------------------------------------------------------------------
TOOL_FUNCTIONS = {
    "get_occupancy_overview": get_occupancy_overview,
    "get_department_workload": get_department_workload,
    "get_waiting_times": get_waiting_times,
    "get_staffing_status": get_staffing_status,
    "get_anomalies": get_anomalies,
    "forecast_admissions_tool": forecast_admissions_tool,
    "predict_wait_time_tool": predict_wait_time_tool,
    "get_bed_availability": get_bed_availability,
    "simulate_reallocation": simulate_reallocation,
    "execute_sql": execute_sql,
}


def _tool(name: str, desc: str, params: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {"type": "object", "properties": params, "required": required},
        },
    }


OLLAMA_TOOLS = [
    _tool("get_occupancy_overview", "Current overall and per-department bed occupancy with status.", {}, []),
    _tool("get_department_workload", "Composite workload stress index (0-100) per department.", {}, []),
    _tool("get_waiting_times", "ER waiting time summary, by urgency and by shift.", {}, []),
    _tool("get_staffing_status", "Nurse-to-patient ratio per department and shift; flags danger zones.", {}, []),
    _tool("get_anomalies", "All current operational anomalies that may require action.", {}, []),
    _tool("forecast_admissions_tool", "Forecast daily admission volume ahead.", {
        "department_id": {"type": "integer", "description": "Optional department id (1-8); omit for hospital-wide."},
        "horizon": {"type": "integer", "description": "Days to forecast (default 7)."},
    }, []),
    _tool("predict_wait_time_tool", "Predict ER wait time for a scenario using the real-data ML model.", {
        "urgency": {"type": "string", "description": "Critical | High | Medium | Low"},
        "nurse_patient_ratio": {"type": "number", "description": "Patients per nurse (1-5)."},
        "er_occupancy": {"type": "number", "description": "ER occupancy 0-1."},
        "shift": {"type": "string", "description": "Morning | Evening | Night"},
        "specialist_availability": {"type": "integer", "description": "Specialists available (0-5)."},
    }, ["urgency", "nurse_patient_ratio", "er_occupancy"]),
    _tool("get_bed_availability", "Project bed availability for a department and when a shortage is expected.", {
        "department_id": {"type": "integer", "description": "Department id (1-8)."},
        "horizon_days": {"type": "integer", "description": "Days ahead (default 5)."},
    }, ["department_id"]),
    _tool("simulate_reallocation", "Simulate moving patients from one ward to another; shows occupancy after the move.", {
        "from_department": {"type": "string", "description": "Source department name."},
        "to_department": {"type": "string", "description": "Destination department name."},
        "patients": {"type": "integer", "description": "Number of patients to move."},
    }, ["from_department", "to_department", "patients"]),
    _tool("execute_sql", "Run a read-only SELECT for ad-hoc evidence from the warehouse.", {
        "query": {"type": "string", "description": "A single read-only SELECT statement."},
    }, ["query"]),
]
