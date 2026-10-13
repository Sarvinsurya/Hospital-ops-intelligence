"""
AI Investigation Agent (Ollama + qwen2.5:3b, local & private).

Implements the abstract's Agent Function:
  * Trigger Detection       — scan anomalies; auto-build an investigation prompt.
  * Root-Cause Investigation— multi-step tool calling to correlate signals.
  * Evidence-Based Recommend— structured NL report (root cause + evidence + action).
  * Explainability          — the full tool-call trace is returned & stored.

The agent uses Ollama's native /api/chat tool-calling. Every investigation is
logged as an "incident" so the UI can show a history.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

import requests

from app.core.config import settings
from app.agent.tools import TOOL_FUNCTIONS, OLLAMA_TOOLS
from app.ml import anomaly

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Hospital Operations Intelligence Agent — an expert hospital operations analyst and decision-support advisor.

You investigate operational problems (bed shortages, long ER waits, staffing gaps, admission surges) using a suite of live analytical tools that query a real hospital data warehouse. You NEVER invent numbers — you call tools to get evidence.

Available tools:
- get_occupancy_overview: current overall + per-department bed occupancy
- get_department_workload: composite workload stress index per department
- get_waiting_times: ER wait times overall / by urgency / by shift
- get_staffing_status: nurse-to-patient ratios per department and shift (danger zones)
- get_anomalies: all current operational anomalies
- forecast_admissions_tool: forecast upcoming admission volume
- predict_wait_time_tool: predict ER wait time for a scenario (real-data ML model)
- get_bed_availability: project when a department will hit a bed shortage
- simulate_reallocation: test moving patients between wards and see resulting occupancy
- execute_sql: read-only SELECT for any ad-hoc evidence

Investigation workflow:
1. Understand the operational question or triggered alert.
2. Call the tools needed to gather concrete evidence (occupancy, staffing, forecasts).
3. Correlate signals to find the ROOT CAUSE (e.g. a high-occupancy ward coinciding with a night-shift staffing gap).
4. When recommending patient moves or staffing changes, VALIDATE them with simulate_reallocation or predict_wait_time_tool.

Final answer MUST use exactly this structure:
**Root Cause**: the identified underlying cause.
**Evidence**: concrete figures from the tools (occupancy %, patients/nurse, forecasts) with department names.
**Recommendation**: specific actionable steps, e.g. "Redirect 3 admissions from Emergency (100% occupancy) to Maternity (62% occupancy)" or "Add 2 nurses to ICU Night shift".
**Explainability**: one or two sentences on the data and reasoning linking evidence to the recommendation.

Rules: be concise and precise, cite exact numbers, prefer feasible actions (check spare capacity), and never fabricate data."""


class HospitalAgent:
    def __init__(self):
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model
        self.max_tool_calls = settings.agent_max_tool_calls

    def check_connection(self) -> tuple[bool, str]:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=4)
            if r.status_code != 200:
                return False, f"Ollama HTTP {r.status_code}"
            names = [m.get("name", "") for m in r.json().get("models", [])]
            ok = any(self.model in n or n.startswith(self.model.split(":")[0]) for n in names)
            return (ok, f"Connected ({self.model})" if ok else f"Model {self.model} not found. Have: {names}")
        except requests.exceptions.ConnectionError:
            return False, f"Cannot reach Ollama at {self.base_url}. Run `ollama serve`."
        except Exception as e:
            return False, f"Ollama check failed: {e}"

    def _chat(self, messages: list[dict], use_tools: bool = True) -> dict:
        payload = {"model": self.model, "messages": messages, "stream": False}
        if use_tools:
            payload["tools"] = OLLAMA_TOOLS
        r = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=180)
        r.raise_for_status()
        return r.json()

    def investigate(self, user_query: str) -> dict:
        """Run a multi-step tool-augmented investigation."""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_query},
        ]
        trace: list[dict] = []
        tools_used: list[str] = []

        try:
            for _ in range(self.max_tool_calls):
                resp = self._chat(messages)
                msg = resp.get("message", {})
                calls = msg.get("tool_calls") or []
                if not calls:
                    answer = msg.get("content", "").strip()
                    return {
                        "answer": answer,
                        "tools_used": tools_used,
                        "trace": trace,
                        "error": None,
                    }
                # append assistant turn that requested tools
                messages.append(msg)
                for call in calls:
                    fn = call.get("function", {})
                    name = fn.get("name", "")
                    args = fn.get("arguments", {}) or {}
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except Exception:
                            args = {}
                    result = self._run_tool(name, args)
                    tools_used.append(name)
                    trace.append({"tool": name, "arguments": args, "result_preview": _preview(result)})
                    messages.append({"role": "tool", "content": json.dumps(result, default=str)[:4000]})

            # exhausted tool budget -> force a final synthesis without tools
            messages.append({"role": "user", "content": "Now give your final structured answer using the evidence gathered."})
            final = self._chat(messages, use_tools=False)
            return {
                "answer": final.get("message", {}).get("content", "").strip(),
                "tools_used": tools_used,
                "trace": trace,
                "error": None,
            }
        except requests.exceptions.ConnectionError:
            return {"answer": "", "tools_used": tools_used, "trace": trace,
                    "error": f"Cannot reach Ollama at {self.base_url}. Is `ollama serve` running?"}
        except Exception as e:
            logger.exception("agent investigation failed")
            return {"answer": "", "tools_used": tools_used, "trace": trace, "error": str(e)}

    def _run_tool(self, name: str, args: dict) -> dict:
        fn = TOOL_FUNCTIONS.get(name)
        if fn is None:
            return {"error": f"unknown tool {name}"}
        try:
            return fn(**args)
        except TypeError as e:
            return {"error": f"bad arguments for {name}: {e}"}
        except Exception as e:
            return {"error": f"{name} failed: {e}"}

    # ---- Trigger detection -------------------------------------------------
    def detect_triggers(self) -> list[dict]:
        """Return current anomalies that should trigger an investigation."""
        return anomaly.detect_all()["anomalies"]

    def auto_investigate(self) -> dict:
        """Pick the most severe current anomaly and investigate it automatically."""
        anomalies = self.detect_triggers()
        if not anomalies:
            return {"triggered": False, "message": "No anomalies above threshold.", "investigation": None}
        crit = [a for a in anomalies if a.get("severity") == "critical"] or anomalies
        top = crit[0]
        q = (
            f"ALERT: {top['message']} (type: {top['type']}). "
            "Investigate the root cause and recommend a specific corrective action with evidence."
        )
        inv = self.investigate(q)
        return {"triggered": True, "trigger": top, "investigation": inv}


def _preview(result) -> str:
    s = json.dumps(result, default=str)
    return s[:500] + ("…" if len(s) > 500 else "")
