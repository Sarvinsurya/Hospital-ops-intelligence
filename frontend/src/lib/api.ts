import axios from "axios";

const api = axios.create({ baseURL: "/api", timeout: 200000 });

// ---- types ----
export interface OccupancyOverall {
  date: string; beds_occupied: number; total_beds: number;
  available_beds: number; occupancy_rate: number; status: string;
}
export interface DeptOccupancy extends OccupancyOverall { department_id: number; department_name: string; }
export interface Summary {
  generated_at: string;
  occupancy: OccupancyOverall;
  waiting_time: { avg_wait_min: number; max_wait_min: number; min_wait_min: number; status: string };
  admissions_today: number;
  emergency_share: number;
}
export interface Workload {
  department_id: number; department_name: string; workload_index: number;
  occupancy_rate: number; admissions_today: number; avg_nurses: number;
  patients_per_nurse: number; status: string;
}
export interface Anomaly {
  type: string; severity: string; message: string;
  department?: string; shift?: string; date?: string; value?: number;
}
export interface Investigation {
  answer: string; tools_used: string[];
  trace: { tool: string; arguments: any; result_preview: string }[];
  error: string | null;
}
export interface Incident {
  id: number; created_at: string; trigger_type: string; severity: string;
  title: string; query: string; answer: string; tools_used: string[]; trace: any[];
}

// ---- analytics ----
export const getSummary = () => api.get<Summary>("/analytics/summary").then(r => r.data);
export const getOccupancyByDept = () => api.get<DeptOccupancy[]>("/analytics/occupancy/by-department").then(r => r.data);
export const getOccupancyTrend = (days = 30) => api.get(`/analytics/occupancy/trend?days=${days}`).then(r => r.data);
export const getAdmissionsDaily = (days = 30) => api.get(`/analytics/admissions/daily?days=${days}`).then(r => r.data);
export const getWaitingTimes = () => api.get("/analytics/waiting-times").then(r => r.data);
export const getWorkload = () => api.get<Workload[]>("/analytics/workload").then(r => r.data);
export const getPatientFlow = (days = 14) => api.get(`/analytics/patient-flow?days=${days}`).then(r => r.data);
export const getSankey = () => api.get("/analytics/patient-flow/sankey").then(r => r.data);
export const getEmergencyVsElective = () => api.get("/analytics/emergency-vs-elective").then(r => r.data);
export const getAlos = () => api.get("/analytics/alos").then(r => r.data);
export const getStaffing = () => api.get("/analytics/staffing").then(r => r.data);

// ---- ml ----
export const getForecast = (dept?: number, horizon = 7) =>
  api.get(`/ml/forecast/admissions?${dept ? `department_id=${dept}&` : ""}horizon=${horizon}`).then(r => r.data);
export const predictWait = (body: any) => api.post("/ml/predict/wait-time", body).then(r => r.data);
export const getWaitSensitivity = (urgency = "High", shift = "Evening") =>
  api.get(`/ml/predict/wait-time/sensitivity?urgency=${urgency}&shift=${shift}`).then(r => r.data);
export const getWaitModelMeta = () => api.get("/ml/model/wait-time/meta").then(r => r.data);
export const getBedAvailability = (dept: number, horizon = 5) =>
  api.get(`/ml/bed-availability/${dept}?horizon_days=${horizon}`).then(r => r.data);
export const getBedAvailabilityAll = (horizon = 5) => api.get(`/ml/bed-availability?horizon_days=${horizon}`).then(r => r.data);
export const getAnomalies = () => api.get("/ml/anomalies").then(r => r.data);

// ---- agent ----
export const getAgentHealth = () => api.get("/agent/health").then(r => r.data);
export const investigate = (query: string, log = true) =>
  api.post<Investigation>("/agent/investigate", { query, log }).then(r => r.data);
export const getTriggers = () => api.get("/agent/triggers").then(r => r.data);
export const autoInvestigate = () => api.post("/agent/auto-investigate").then(r => r.data);
export const simulateReallocation = (from_department: string, to_department: string, patients: number) =>
  api.post("/agent/simulate-reallocation", { from_department, to_department, patients }).then(r => r.data);
export const getIncidents = (limit = 50) => api.get<Incident[]>(`/agent/incidents?limit=${limit}`).then(r => r.data);

// ---- meta ----
export const getDepartments = () => api.get("/meta/departments").then(r => r.data);
export const getDataSource = () => api.get("/meta/data-source").then(r => r.data);

export default api;
