"""Analytics / KPI endpoints."""
from fastapi import APIRouter, Query

from app.analytics import kpis

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
def summary():
    return kpis.dashboard_summary()


@router.get("/occupancy/overall")
def occupancy_overall():
    return kpis.bed_occupancy_overall()


@router.get("/occupancy/by-department")
def occupancy_by_department():
    return kpis.bed_occupancy_by_department()


@router.get("/occupancy/trend")
def occupancy_trend(days: int = Query(30, ge=7, le=180)):
    return kpis.occupancy_trend(days)


@router.get("/admissions/daily")
def admissions_daily(days: int = Query(30, ge=7, le=180)):
    return kpis.admission_volume_daily(days)


@router.get("/admissions/weekly")
def admissions_weekly():
    return kpis.admission_volume_weekly()


@router.get("/waiting-times")
def waiting_times():
    return {
        "summary": kpis.waiting_time_summary(),
        "by_urgency": kpis.waiting_time_by_urgency(),
        "by_shift": kpis.waiting_time_by_shift(),
    }


@router.get("/workload")
def workload():
    return kpis.department_workload_index()


@router.get("/patient-flow")
def patient_flow(days: int = Query(14, ge=7, le=60)):
    return kpis.patient_flow(days)


@router.get("/patient-flow/sankey")
def patient_flow_sankey():
    return kpis.patient_flow_sankey()


@router.get("/emergency-vs-elective")
def emergency_vs_elective():
    return kpis.emergency_vs_elective()


@router.get("/alos")
def alos():
    return kpis.alos_by_department()


@router.get("/staffing")
def staffing():
    return kpis.staffing_efficiency()
