"""Agent endpoints: investigation, triggers, auto-investigate, reallocation sim, incidents."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agent.agent import HospitalAgent
from app.agent import incidents, tools

router = APIRouter(prefix="/agent", tags=["agent"])
_agent = HospitalAgent()


@router.get("/health")
def agent_health():
    ok, msg = _agent.check_connection()
    return {"connected": ok, "message": msg, "model": _agent.model}


class InvestigateInput(BaseModel):
    query: str
    log: bool = True


@router.post("/investigate")
def investigate(inp: InvestigateInput):
    result = _agent.investigate(inp.query)
    if inp.log and not result.get("error"):
        incidents.log_incident(
            title=inp.query[:80], query=inp.query,
            investigation=result, trigger_type="manual", severity="info",
        )
    return result


@router.get("/triggers")
def triggers():
    return {"anomalies": _agent.detect_triggers()}


@router.post("/auto-investigate")
def auto_investigate():
    result = _agent.auto_investigate()
    if result.get("triggered") and result.get("investigation") and not result["investigation"].get("error"):
        trig = result["trigger"]
        incidents.log_incident(
            title=trig.get("message", "Auto investigation")[:80],
            query=trig.get("message", ""),
            investigation=result["investigation"],
            trigger_type=trig.get("type", "auto"),
            severity=trig.get("severity", "warning"),
        )
    return result


class ReallocationInput(BaseModel):
    from_department: str
    to_department: str
    patients: int


@router.post("/simulate-reallocation")
def simulate_reallocation(inp: ReallocationInput):
    return tools.simulate_reallocation(inp.from_department, inp.to_department, inp.patients)


@router.get("/incidents")
def list_incidents(limit: int = 50):
    return incidents.list_incidents(limit)


@router.get("/incidents/{incident_id}")
def get_incident(incident_id: int):
    inc = incidents.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return inc
