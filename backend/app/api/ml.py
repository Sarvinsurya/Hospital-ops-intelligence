"""ML endpoints: forecasting, wait-time prediction, bed availability, anomalies."""
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.ml import forecasting, wait_time, bed_availability, anomaly

router = APIRouter(prefix="/ml", tags=["ml"])


@router.get("/forecast/admissions")
def forecast_admissions(department_id: int | None = None, horizon: int = Query(7, ge=1, le=30)):
    return forecasting.forecast_admissions(department_id, horizon)


@router.get("/forecast/by-shift")
def forecast_by_shift(department_id: int, horizon_days: int = Query(2, ge=1, le=7)):
    return forecasting.forecast_by_shift(department_id, horizon_days)


class WaitInput(BaseModel):
    urgency: str
    nurse_patient_ratio: float
    er_occupancy: float
    shift: str = "Morning"
    specialist_availability: int = 3


@router.post("/predict/wait-time")
def predict_wait(inp: WaitInput):
    return wait_time.predict(
        inp.urgency, inp.nurse_patient_ratio, inp.er_occupancy,
        inp.shift, inp.specialist_availability,
    )


@router.get("/predict/wait-time/sensitivity")
def wait_sensitivity(urgency: str = "High", shift: str = "Evening"):
    return wait_time.sensitivity_curve(urgency, shift)


@router.get("/model/wait-time/meta")
def wait_model_meta():
    return wait_time.train()


@router.get("/bed-availability/{department_id}")
def bed_avail(department_id: int, horizon_days: int = Query(5, ge=1, le=14)):
    return bed_availability.bed_availability_forecast(department_id, horizon_days)


@router.get("/bed-availability")
def bed_avail_all(horizon_days: int = Query(5, ge=1, le=14)):
    return bed_availability.all_departments_availability(horizon_days)


@router.get("/anomalies")
def anomalies():
    return anomaly.detect_all()
