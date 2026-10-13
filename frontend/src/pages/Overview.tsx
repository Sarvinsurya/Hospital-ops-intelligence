import { useEffect, useState } from "react";
import ReactECharts from "echarts-for-react";
import { motion } from "framer-motion";
import { AlertTriangle, TrendingUp, BedDouble, Clock } from "lucide-react";
import { Card, StatusBadge } from "../components/ui";
import Gauge from "../components/Gauge";
import {
  getSummary, getOccupancyByDept, getAdmissionsDaily, getAnomalies, getForecast,
  type Summary, type DeptOccupancy,
} from "../lib/api";

const AX = { color: "#6b7280", fontSize: 10 };
const SPLIT = { lineStyle: { color: "#232732" } };

export default function Overview() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [depts, setDepts] = useState<DeptOccupancy[]>([]);
  const [adm, setAdm] = useState<any[]>([]);
  const [forecast, setForecast] = useState<any>(null);
  const [anomalies, setAnomalies] = useState<any>({ anomalies: [], total: 0, critical_count: 0 });

  useEffect(() => {
    getSummary().then(setSummary);
    getOccupancyByDept().then(setDepts);
    getAdmissionsDaily(30).then(setAdm);
    getAnomalies().then(setAnomalies);
    getForecast(undefined, 7).then(setForecast);
  }, []);

  const admDates = adm.map((d) => d.date.slice(5));
  const fcHist = forecast?.history ?? [];
  const fcFut = forecast?.forecast ?? [];

  const admissionsOption = {
    grid: { left: 40, right: 16, top: 20, bottom: 24 },
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: admDates, axisLabel: AX, axisLine: { lineStyle: { color: "#2d323f" } } },
    yAxis: { type: "value", axisLabel: AX, splitLine: SPLIT },
    series: [{
      type: "bar", data: adm.map((d) => d.admissions),
      itemStyle: { color: "#d4f23a", borderRadius: [3, 3, 0, 0] }, barWidth: "55%",
    }],
  };

  const forecastOption = {
    grid: { left: 40, right: 16, top: 20, bottom: 24 },
    tooltip: { trigger: "axis" },
    legend: { data: ["History", "Forecast"], textStyle: { color: "#8b92a3" }, top: 0, right: 0 },
    xAxis: {
      type: "category",
      data: [...fcHist.map((h: any) => h.date.slice(5)), ...fcFut.map((f: any) => f.date.slice(5))],
      axisLabel: AX, axisLine: { lineStyle: { color: "#2d323f" } },
    },
    yAxis: { type: "value", axisLabel: AX, splitLine: SPLIT },
    series: [
      { name: "History", type: "line", smooth: true, symbol: "none",
        data: fcHist.map((h: any) => h.admissions),
        lineStyle: { color: "#5ca8ff", width: 2 }, areaStyle: { color: "rgba(92,168,255,0.08)" } },
      { name: "Forecast", type: "line", smooth: true, symbol: "circle", symbolSize: 5,
        data: [...Array(fcHist.length).fill(null), ...fcFut.map((f: any) => f.predicted_admissions)],
        lineStyle: { color: "#d4f23a", width: 2, type: "dashed" }, itemStyle: { color: "#d4f23a" } },
    ],
  };

  const occ = summary ? summary.occupancy.occupancy_rate * 100 : 0;
  const wait = summary ? Math.min(100, (summary.waiting_time.avg_wait_min / 120) * 100) : 0;

  return (
    <div className="space-y-6">
      {/* Top row: gauges + stat cards */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
        <Card title="Bed Occupancy">
          <Gauge value={occ} label="hospital-wide" thresholds={{ warning: 80, critical: 90 }} />
        </Card>
        <Card title="ER Wait Load">
          <Gauge value={wait} label={`${summary?.waiting_time.avg_wait_min ?? 0} min avg`} suffix="" thresholds={{ warning: 33, critical: 50 }} />
        </Card>
        <div className="grid grid-cols-1 gap-6 lg:col-span-2 lg:grid-cols-2">
          <StatCard icon={<BedDouble size={18} />} label="Available Beds"
            value={`${summary?.occupancy.available_beds ?? "—"}`} sub={`of ${summary?.occupancy.total_beds ?? "—"} total`} />
          <StatCard icon={<TrendingUp size={18} />} label="Admissions Today"
            value={`${summary?.admissions_today ?? "—"}`} sub="live count" />
          <StatCard icon={<Clock size={18} />} label="Max Wait"
            value={`${summary?.waiting_time.max_wait_min ?? "—"}m`} sub="longest in ER" />
          <StatCard icon={<AlertTriangle size={18} />} label="Active Anomalies"
            value={`${anomalies.total}`} sub={`${anomalies.critical_count} critical`}
            danger={anomalies.critical_count > 0} />
        </div>
      </div>

      {/* Middle: occupancy by dept + admissions */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card title="Occupancy by Department" className="lg:col-span-1">
          <div className="space-y-3">
            {depts.map((d) => (
              <OccupancyBar key={d.department_id} d={d} />
            ))}
          </div>
        </Card>
        <Card title="Daily Admissions (30d)" className="lg:col-span-2">
          <ReactECharts option={admissionsOption} style={{ height: 260 }} notMerge />
        </Card>
      </div>

      {/* Bottom: forecast + anomaly feed */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card title={`Admission Forecast · ${forecast?.model ?? ""}`} className="lg:col-span-2">
          <ReactECharts option={forecastOption} style={{ height: 260 }} notMerge />
        </Card>
        <Card title="Anomaly Feed">
          <div className="space-y-2 max-h-[260px] overflow-y-auto pr-1">
            {anomalies.anomalies.length === 0 && <p className="text-sm text-muted">No anomalies.</p>}
            {anomalies.anomalies.map((a: any, i: number) => (
              <motion.div key={i} initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.04 }}
                className="flex items-start gap-2 rounded-lg border border-ink-400/50 bg-ink-700/50 p-2.5">
                <span className="mt-1 h-2 w-2 shrink-0 rounded-full"
                  style={{ background: a.severity === "critical" ? "#ff5c5c" : "#ffb545" }} />
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] uppercase tracking-wide text-muted">{a.type.replace(/_/g, " ")}</span>
                    <StatusBadge status={a.severity} />
                  </div>
                  <p className="text-xs text-slate-300">{a.message}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, sub, danger }: any) {
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
      className="glass-card flex flex-col justify-between p-4">
      <div className="flex items-center gap-2 text-muted">{icon}<span className="text-xs">{label}</span></div>
      <div className={`mt-2 text-3xl font-bold ${danger ? "text-status-critical" : "text-slate-100"}`}>{value}</div>
      <div className="text-[11px] text-muted">{sub}</div>
    </motion.div>
  );
}

function OccupancyBar({ d }: { d: DeptOccupancy }) {
  const pct = d.occupancy_rate * 100;
  const color = pct >= 90 ? "#ff5c5c" : pct >= 80 ? "#ffb545" : "#d4f23a";
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="text-slate-300">{d.department_name}</span>
        <span className="font-mono text-muted">{d.beds_occupied}/{d.total_beds} · {pct.toFixed(0)}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-ink-500">
        <motion.div initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 0.7, ease: "easeOut" }}
          className="h-full rounded-full" style={{ background: color, boxShadow: `0 0 10px ${color}88` }} />
      </div>
    </div>
  );
}
