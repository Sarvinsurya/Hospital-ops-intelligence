# Hospital Operations Intelligence System — Demo & Presentation Guide

> A step-by-step script for presenting the project to staff/evaluators.
> Follow the flow top to bottom. Each page has: **what it is → how to demo it → what to say.**

---

## 0. The 30-second pitch (say this first)

> "Hospitals generate huge amounts of operational data — admissions, beds, waiting
> times, staffing — but most still rely on manual reports and react *after* problems
> happen. Our **Hospital Operations Intelligence System** turns that data into a
> live control room. It tracks every key metric in real time, uses **machine learning**
> to forecast demand and predict waiting times, and runs an **AI agent** that
> investigates problems and recommends exactly what to do — with evidence. It's a
> complete pipeline: **Data → ETL → Warehouse → BI Dashboards → ML Models → AI Agent →
> Evidence-Based Recommendations.**"

---

## 0.5. The main KPIs this project tracks

These are the core hospital-operations metrics the whole system is built around. Each one
is computed live from the data warehouse and surfaced on the dashboards.

| # | KPI | What it measures | Where shown |
|---|-----|------------------|-------------|
| 1 | **Bed Occupancy Rate** | % of beds in use — overall and per department (with status: normal/warning/critical) | Overview gauge, Departments |
| 2 | **Daily & Weekly Admission Volume** | How many patients are admitted per day / week (the inflow) | Overview |
| 3 | **Average Patient Waiting Time** | Mean ER wait (triage→treatment), broken down by urgency and shift | Waiting Times, top-bar pill |
| 4 | **Department Workload Index** | A composite 0–100 stress score per ward (occupancy + admissions pressure + nurse load) | Departments |
| 5 | **Patient Flow** | Arrivals, transfers, and discharges — how patients move through the hospital | Patient Flow |
| 6 | **Emergency vs Elective Split** | Share of admissions that are emergency vs planned | Overview, top-bar pill |
| 7 | **Average Length of Stay (ALOS)** | Average days a patient stays, per department | Departments |
| 8 | **Nurse-to-Patient Ratio (Staffing)** | Patients per nurse by department × shift; flags unsafe "danger zones" | Staffing |

**How to say it in one line:**
> "We focus on eight core KPIs — bed occupancy, admission volume, average waiting time,
> department workload, patient flow, emergency-vs-elective split, length of stay, and
> nurse-to-patient staffing ratio. Together they give a complete, real-time picture of
> hospital capacity and patient throughput."

> On top of these live KPIs, the system layers **ML forecasts** (patient volume, waiting
> time, bed availability), **anomaly detection**, and the **AI investigation agent**.

---

## 1. The architecture (one diagram to show)

```
   Kaggle datasets (real)
   ├─ ER Wait Time (5,000 real visits)
   └─ Hospital Beds Management (weekly beds + 1,000 patients + staff)
            │
            ▼
         ETL  ──►  SQLite Data Warehouse
                        │
        ┌───────────────┼────────────────┐
        ▼               ▼                ▼
   Analytics        ML Models        AI Agent (Ollama · qwen2.5:3b)
   (12 KPIs)   (forecast / wait /    (10 tools, investigates,
                beds / anomaly)       recommends, explains)
        └───────────────┼────────────────┘
                        ▼
              FastAPI REST API (33 endpoints)
                        │
                        ▼
          React Control-Room UI (8 pages)
```

**Key talking points about the architecture:**
- **Two tiers** — a Python backend and a React frontend, talking over a REST API. This is professional, production-style separation (not a single script).
- **Real data** — the waiting-time model is trained on the **real Kaggle ER dataset** . We'll prove this on the Data Source page.
- **Runs 100% locally & private** — the AI agent uses **Ollama** on this machine. No cloud, no API keys, no patient data leaving the building — important for healthcare.

---

## 2. Before the demo — start the system

Run **one command** and everything comes up with health checks:

- **Mac:** `./start.sh`
- **Windows:** double-click `start.bat`

Wait for the green banner:
```
✅ ALL SYSTEMS GO
🖥  Frontend:  http://localhost:5190
```
It opens the browser automatically. If asked, mention:
> "The launcher detects the OS, installs anything missing, builds the data
> warehouse, starts both servers, and runs 6 health checks before telling us it's ready."

**Pre-demo checklist (do this 5 min before):**
- [ ] Ollama is running (`ollama serve`) and `qwen2.5:3b` is pulled — needed for the AI War Room.
- [ ] The top bar shows **Agent: online** (green dot). If red, the agent page still loads but won't answer.
- [ ] The top-bar KPI pills show live numbers (Occupancy, Avg Wait, Admissions, Emergency).

---

## 3. The guided tour — page by page

> Navigate using the **icon rail** on the far left. Go in THIS order — it builds a story
> from "what's happening" → "what will happen" → "what should we do."

The top bar is always visible: it shows the **4 headline KPIs as live pills** and an
**Agent online** indicator. Point this out once:
> "These pills update live every 30 seconds — occupancy, average wait, admissions
> today, and the emergency share. This is our always-on pulse of the hospital."

---

### PAGE 1 — Overview (the control room) 🖥 *icon: dashboard*

**What it is:** the main real-time dashboard — the single screen a hospital manager
would keep open all day.

**How to demo:**
1. Point to the two **gauges** at the top: **Bed Occupancy** and **ER Wait Load**.
   - "Just like a car dashboard. Green is healthy, amber is a warning, red is critical.
     The needle animates to the live value."
2. Point to the four **stat cards**: Available Beds, Admissions Today, Max Wait,
   Active Anomalies. "Active Anomalies turns red when something needs attention."
3. Point to **Occupancy by Department** — animated bars, color-coded by status.
   "You can instantly see which wards are full (red) and which have room (green)."
4. Point to **Daily Admissions (30 days)** — the trend of patient inflow.
5. Point to the **Admission Forecast** chart — "The solid blue line is history, the
   dashed green line is our **ML forecast** for the next 7 days. This is predictive,
   not just reporting."
6. Point to the **Anomaly Feed** on the right — a live list of problems detected
   automatically (occupancy breaches, staffing danger, admission spikes).

**What to say:**
> "This one screen answers 'what is happening right now?' — occupancy, admissions,
> waits, and auto-detected anomalies — plus a 7-day ML forecast of what's coming."

**Deep-dive Q&A (if asked about the Overview page):**

- **Q: What model powers the Admission Forecast?**
  **Holt-Winters Exponential Smoothing** (triple exponential smoothing, from `statsmodels`),
  configured with `trend="add"`, `seasonal="add"`, `seasonal_periods=7`. It forecasts the
  next 7 days of admissions. It tracks three components — **Level** (baseline), **Trend**
  (drift up/down), and **Seasonality** (the repeating 7-day weekday pattern); the forecast =
  Level + Trend + that day's seasonal factor, weighting recent days more. The shaded band is
  a **95% confidence interval** (prediction ± 1.96 × residual std-dev). If history < 21 days,
  it falls back to a **seasonal-naive** model. *(This is separate from the Waiting-Times ML
  model, which is Gradient Boosting on real ER data.)*

- **Q: How does the Anomaly Feed work?**
  Four detectors run and combine. Two are **statistical (z-score)**, two are **threshold rules**:
  - *Admission spike* & *Wait anomaly* use a **z-score**: `z = (today − rolling 14-day mean) /
    rolling 14-day std-dev`. Flagged when **z ≥ 2.3** (warning) or **z ≥ 3.0** (critical) — i.e.
    unusual *relative to the hospital's own recent norm*.
  - *Occupancy breach*: ward occupancy **≥ 80% → warning, ≥ 90% → critical** (fixed thresholds).
  - *Staffing danger*: **patients-per-nurse ≥ 8 → danger** (≥ ~10.4 → critical).

- **Q: What are "Active Anomalies" / what counts as one?**
  The **count of all problems detected right now** (card also shows how many are *critical*).
  Five types can appear: **occupancy breach, staffing danger, admission spike, wait anomaly,
  discharge drop.** Severity = *warning* (watch) or *critical* (act now). These same anomalies
  become the **"Active Triggers"** on the AI War Room page, and the critical ones drive the
  agent's **Auto-Investigate** — so the feed is also the trigger mechanism for the AI agent.

---

### PAGE 2 — Departments (deep dive + proactive beds) 📈 *icon: activity*

**What it is:** per-department workload and a forward-looking bed-availability forecast.

**How to demo:**
1. Top section — **Department Workload Index** cards. "Each ward gets a composite
   stress score from 0–100, combining occupancy, admissions pressure, and nurse load.
   One number tells you how stressed a ward is." Point to a red (critical) card.
2. **Bed Availability Forecast** — the colored day-strips. "For each department we
   project the next 5 days. If a strip turns red, we're forecasting a **bed shortage
   on that day** — so staff can act *before* it happens, not after."
3. **Average Length of Stay** chart — "ICU and Surgery keep patients longest; this
   drives how fast beds free up."

**What to say:**
> "This page moves from *reacting* to *anticipating*. The workload index ranks our
> most-stressed wards, and the availability forecast tells us a shortage is coming
> days in advance."

---

### PAGE 3 — Waiting Times (REAL data + interactive ML) ⏱ *icon: clock*

**What it is:** the waiting-time analytics plus a **live, interactive ML predictor**.
*This is a highlight — spend time here.*

**How to demo:**
1. **Avg ER Wait by Urgency** chart — "Notice Critical patients wait the least and
   Low-urgency wait the most. That's correct triage behavior — and this is from the
   **real Kaggle ER dataset of 5,000 visits.**"
2. **Avg ER Wait by Shift** — "Night shift waits are longest — a real staffing signal."
3. **THE INTERACTIVE PREDICTOR** (the showpiece):
   - "Watch this." Move the **Patients-per-nurse slider** up → click **Predict**.
   - "The predicted wait jumps. Now change urgency to **Critical** → it drops.
     This is a **machine-learning model trained on the real data** — it learned that
     wait time depends on urgency, nurse ratio, occupancy, and shift."
   - Point to the title: **R²=0.80, MAE≈20 min** → "That's the model's accuracy."
4. **Sensitivity curve** — "This shows exactly how wait time rises as each nurse has
   to cover more patients. It's the evidence behind our staffing recommendations."

**What to say:**
> "This is real machine learning on real hospital data. Administrators can ask
> 'what if we're short-staffed tonight?' and get a predicted waiting time instantly."

**Deep-dive Q&A — what do "R²=0.80" and "MAE≈20 min" mean?**

These are the model's **accuracy scores**, measured on a **20% held-out test set** — 1,000 real
visits the model never saw during training (we train on 80%, test on the other 20%). Testing on
unseen data is what makes the numbers honest.

- **MAE — Mean Absolute Error** → "on average, how many minutes off we are."
  - Formula: `MAE = (1/n) × Σ | actual − predicted |` (average of the prediction errors, ignoring sign).
  - **MAE ≈ 20 min** → "our predicted wait is, on average, within ~20 minutes of the real wait."
    Same unit as the thing predicted (minutes), so it's intuitive. Lower = better.

- **R² — R-squared (coefficient of determination)** → "how much of the variation in waiting times
  the model explains," scored 0 to 1.
  - Formula: `R² = 1 − (SS_res / SS_tot)` where `SS_res = Σ(actual − predicted)²` (error left over)
    and `SS_tot = Σ(actual − mean)²` (total variation). It compares the model to simply guessing the
    average wait every time.
  - **R² = 0.80** → "the model explains 80% of *why* one patient waits longer than another; only
    20% is unexplained noise." For messy real-world hospital data, 0.80 is a strong result.
  - Scale: 1.0 = perfect, 0 = no better than guessing the average.

- **Both are computed with scikit-learn** (`mean_absolute_error`, `r2_score`) on the test split.

> One-liner: *"R² of 0.80 means we explain 80% of the differences in patient waits; MAE of ~20 min
> means we're on average within 20 minutes — both measured on real visits the model never trained on."*

---

### PAGE 4 — Staffing (shift-gap heatmap) 👥 *icon: users*

**What it is:** nurse-to-patient ratios across every department and shift.

**How to demo:**
1. Point to the **heatmap** — departments down the side, shifts across the top.
   "Green is safe staffing, red is dangerous. The eye goes straight to the red cells."
2. "Notice the **Night-shift columns tend to be redder** — fewer nurses, same patients.
   That's the classic hospital danger zone, and our system surfaces it visually."
3. Scroll to **Danger Zones** cards — "These are the specific understaffed shifts that
   need action tonight, with the exact patients-per-nurse number."

**What to say:**
> "Staffing misallocation is a top cause of long waits and burnout. This heatmap turns
> a spreadsheet of rosters into an at-a-glance safety map."

---

### PAGE 5 — Patient Flow (Sankey) 🔀 *icon: branch*

**What it is:** a visual of how patients move through the hospital.

**How to demo:**
1. Point to the **Sankey diagram**: "Patients arrive on the left, flow into
   departments in the middle, then either get transferred or discharged on the right.
   The thickness of each ribbon = the number of patients. Hover to see exact counts."
2. Point to the **flow chart below**: arrivals vs discharges vs transfers over 14 days.
   "When arrivals (blue) run above discharges (green), the hospital is filling up."

**What to say:**
> "This answers 'where are the bottlenecks in patient movement?' at a glance — a view
> you simply can't get from tables of numbers."

---

### PAGE 6 — Reallocation Simulator (what-if) 🔀 *icon: shuffle* ⭐ UNIQUE

**What it is:** a what-if tool to safely test moving patients between wards *before*
committing.

**How to demo:**
1. "The system auto-picks an overcrowded ward (From) and a ward with space (To)."
2. Set **patients to move** with the slider → click **Simulate**.
3. Point to the **Before/After bars** that animate: "Watch the source ward's occupancy
   drop and the destination's rise — in real time, before we touch a single bed."
4. Point to the **feasibility banner**: green ✓ "Feasible" or red ✗ with the reason.
   "It checks the destination actually has enough free beds — no impossible advice."

**What to say:**
> "This is decision support in action. A manager can model a bed transfer and see the
> exact impact instantly, then act with confidence. This is also the same tool the AI
> agent uses to validate its own recommendations."

---

### PAGE 7 — AI War Room (the star of the show) 🤖 *icon: bot* ⭐⭐ HEADLINE

**What it is:** the autonomous AI investigation agent. **This is the climax — slow down.**

**How to demo (do all three):**

**(a) Ask a question in plain English:**
- Click a suggestion chip, e.g. *"Which department is most overcrowded and what should we do?"*
- "Watch — the agent is now **thinking**." (the loader shows it's calling tools.)
- When the report appears, read out the four parts:
  **Root Cause → Evidence → Recommendation → Explainability.**
- "Notice it gives a **specific, actionable** recommendation with real numbers — like
  'redirect 5 patients from Emergency to Orthopedics' — not vague advice."

**(b) Show the Explainability trace (the trust factor):**
- Point to the **"Explainability · tool trace"** box below the answer.
- "This is huge for healthcare. Every recommendation shows **exactly which data tools
  the agent called** and what it found. Nothing is a black box — an administrator can
  verify the reasoning before acting."

**(c) Show Auto-Investigate + Triggers + Incident History (right side):**
- Point to **Active Triggers** — "The system is monitoring thresholds. When occupancy
  passes 90% or waits get too long, it flags a trigger automatically."
- Click **Auto** — "This makes the agent pick the most severe current problem and
  investigate it on its own, with no human prompt."
- Point to **Incident History** — "Every investigation is logged with a timestamp, so
  we have a full audit trail of what was flagged and what was advised."

**What to say:**
> "This is the difference between a dashboard and an *intelligent* system. The agent
> runs **locally and privately** on Ollama, investigates problems like an analyst
> would — gathering evidence, correlating signals — and recommends concrete actions,
> always showing its work."

> **Tip:** also type the simple question *"how long until a patient gets a bed?"* to
> show it answers directly and picks the right tool — proving it understands intent,
> not just keywords.

---

### PAGE 8 — Data Source (credibility) 🗄 *icon: database*

**What it is:** proof of where the data comes from — real vs. generated.

**How to demo:**
1. Point to the three provenance cards:
   - **ER Wait Time (Kaggle · real)** — 5,000 real visits, trains the ML model.
   - **Hospital Beds Management (Kaggle · real)** — real weekly beds + 1,000 patients.
   - **Operational Backbone (synthetic · calibrated)** — "a daily feed we generate,
     *calibrated to the real data's bed counts and length-of-stay*, so the live control
     room is rich and continuous."
2. Point to the **departments table** — beds, target occupancy, ALOS per ward.

**What to say:**
> "We're transparent about our data. The waiting-time intelligence runs on genuine
> Kaggle hospital data; the real-time operational layer is a calibrated simulation so
> the dashboard always has live movement to show. Both are clearly labelled."

---

## 4. Feature checklist (map to the project requirements)

Use this to show you covered **everything** in the abstract, plus extras.

| Requirement (from abstract)              | Where to show it                         |
|------------------------------------------|------------------------------------------|
| Bed occupancy (overall + per dept)       | Overview gauge + Departments             |
| Daily / weekly admission volume          | Overview (daily chart)                   |
| Average patient waiting time             | Waiting Times page                       |
| Department workload index                | Departments (workload cards)             |
| Patient flow (arrivals/transfers/disch.) | Patient Flow (Sankey + chart)            |
| Emergency vs elective split              | Top-bar KPI + summary                    |
| Average length of stay (ALOS)            | Departments (ALOS chart)                 |
| ML: forecast patient volume              | Overview (forecast chart)                |
| ML: predict waiting time                 | Waiting Times (interactive predictor)    |
| ML: estimate bed availability window     | Departments (availability forecast)      |
| Resource/staffing analysis               | Staffing (heatmap + danger zones)        |
| Anomaly / bottleneck detection           | Overview (anomaly feed)                  |
| AI agent: trigger detection              | AI War Room (Active Triggers)            |
| AI agent: root-cause investigation       | AI War Room (Investigate)                |
| AI agent: evidence-based recommendation  | AI War Room (report)                     |
| AI agent: explainability                 | AI War Room (tool trace)                 |

**Extra / unique features that go beyond the brief:**
1. Bed **Reallocation Simulator** (what-if before you act)
2. **Bed-availability forecast strips** (shortage days ahead of time)
3. **Staff shift-gap heatmap**
4. **Patient-flow Sankey** diagram
5. **AI War Room** with auto-investigate + incident history log
6. **Explainability tool-trace** on every recommendation
7. Control-room **gauges** and live KPI pills

---

## 5. The technology (if asked)

- **Backend:** Python, FastAPI (33 REST endpoints), SQLite data warehouse.
- **ETL:** loads real Kaggle CSVs + a calibrated synthetic daily feed into a star-schema warehouse.
- **ML:** scikit-learn (Gradient Boosting for wait-time, trained on real data, R²≈0.80),
  statsmodels (Holt-Winters time-series forecasting), rolling z-score anomaly detection.
- **AI agent:** Ollama running **qwen2.5:3b locally**, native tool-calling with 10
  hospital-ops tools; multi-step investigate → evidence → recommend → explain.
- **Frontend:** React + Vite + TypeScript, TailwindCSS, Framer Motion (animations),
  ECharts (gauges, heatmap, Sankey, charts). Dark "control-room" theme.
- **One-command cross-platform launcher** with automatic dependency install + health checks.

---

## 6. Suggested 5-minute demo flow (if time is short)

1. **Overview** (45s) — "here's the live hospital at a glance" + the ML forecast.
2. **Waiting Times** (60s) — move the sliders, show the **real-data ML predictor**.
3. **Staffing heatmap** (30s) — "instant safety map."
4. **Reallocation Simulator** (45s) — simulate a transfer, show before/after.
5. **AI War Room** (90s) — ask a question, read the report, show the **explainability
   trace**, then click **Auto**. End here — it's the strongest moment.

Close with:
> "So we've gone from raw hospital data all the way to an AI that tells us what's
> wrong and what to do about it — running privately on our own machine. That's the
> full Hospital Operations Intelligence pipeline."

---

## 7. Likely questions & confident answers

- **"Is the data real?"** → "The ER waiting-time data is real Kaggle data and trains
  our ML model. The daily operational feed is a calibrated simulation, clearly labelled
  on the Data Source page. The system also loads real Kaggle CSVs directly if provided."
- **"Does it need the internet / cloud?"** → "No. The AI runs locally via Ollama.
  Fully private — nothing leaves this machine."
- **"How accurate is the wait prediction?"** → "R² of about 0.80 with a mean error
  around 20 minutes, trained on 5,000 real visits."
- **"What if the AI gives a wrong number?"** → "It never invents numbers — it calls
  data tools and shows the exact trace, so every answer is verifiable. It also validates
  bed moves against real spare capacity."
- **"Why a small 3B model?"** → "It runs instantly on a laptop with no cost or cloud.
  We can swap to a larger model with a one-line config change if more accuracy is needed."
