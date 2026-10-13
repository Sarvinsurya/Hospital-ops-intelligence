# Hospital Operations Intelligence System

A BI + ML + AI-Agent platform for hospital operations. It tracks admissions, bed
occupancy, waiting times, department workload and patient flow; forecasts patient
volume and predicts waiting times with ML; and runs a local AI agent that
investigates resource shortages and recommends evidence-based bed/staff allocation.

Built for the BI Laboratory project. Datasets: **ER Wait Time** and **Hospital Beds
Management** (Kaggle) — the ER data is used as-is to train the wait-time model; a
daily operational backbone is synthesised and calibrated to the real bed/ALOS
profile so the real-time control room is rich.

## Architecture

```
Kaggle data ─► ETL ─► SQLite warehouse ─► Analytics (KPIs)
                                        ├─► ML (forecast / wait / beds / anomaly)
                                        └─► AI Agent (Ollama qwen2.5:3b, tool-calling)
                                                   │
                            FastAPI REST API ◄─────┘
                                   │
                       React + Vite control-room UI
```

- **Backend:** FastAPI + SQLite + scikit-learn + statsmodels + Ollama agent
- **Frontend:** React + Vite + TypeScript + TailwindCSS + Framer Motion + ECharts
  (dark "control-room" theme: icon-rail nav, KPI pills, gauges, glass cards)

## Features

Required BI KPIs: bed occupancy (overall + per department + trend), daily/weekly
admissions, average waiting time (by urgency/shift), department workload index,
patient flow (arrivals/transfers/discharges), emergency-vs-elective, ALOS by
department, nurse-to-patient staffing analysis.

ML: patient-volume forecasting (Holt-Winters), dynamic wait-time prediction
(GradientBoosting on **real ER data**, R²≈0.80), bed-availability window
estimation, anomaly/bottleneck detection.

AI agent: trigger detection, multi-step root-cause investigation via tools,
evidence-based recommendations, full explainability trace, incident logging.

Unique features: bed reallocation simulator, bed-availability/surge forecast
strips, staff shift-gap heatmap, patient-flow Sankey, AI war-room with incident
log, explainability tool-trace drawer, control-room gauges.

## Prerequisites

- Python 3.12, Node 18+
- [Ollama](https://ollama.com) running locally with the model:
  `ollama pull qwen2.5:3b`

## Quick start (one command)

A cross-platform launcher detects your OS, installs any missing dependencies,
builds the warehouse if needed, starts both servers, runs health checks, and
opens the UI.

**macOS / Linux:**
```bash
./start.sh
```

**Windows** (double-click `start.bat`, or):
```bat
start.bat
```
or in PowerShell:
```powershell
./start.ps1
```

It prints the links when ready:
- Frontend: http://localhost:5190
- Backend API: http://localhost:8077
- API docs: http://localhost:8077/docs

Options: `--no-install` (skip dependency checks), `--no-open` (don't open browser).
Press **Ctrl+C** to stop both servers.

> Prerequisite for the AI agent: [Ollama](https://ollama.com) running with
> `ollama pull qwen2.5:3b`. The dashboards and ML work even if Ollama is offline;
> only the agent features need it.

## Manual run

**Backend** (port 8077):
```bash
cd backend
python3.12 -m venv venv
./venv/bin/pip install -r requirements.txt
# build the warehouse (also auto-builds on first API startup)
./venv/bin/python -m app.etl.build_warehouse
./venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8077
```

**Frontend** (port 5190, proxies /api → 8077):
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5190

API docs: http://127.0.0.1:8077/docs

## Data

Real Kaggle CSVs live in `backend/data/raw/` (`er_wait/`, `hospital_beds/`). The
ETL loads the real ER data as the `fact_er_visits` fact and the real beds data as
reference tables, and synthesises a calibrated daily operational backbone. The
SQLite warehouse is written to `backend/data/warehouse/hospital_ops.db`.
