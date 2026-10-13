import { useEffect, useState } from "react";
import ReactECharts from "echarts-for-react";
import { motion } from "framer-motion";
import { Card, StatusBadge } from "../components/ui";
import { getWorkload, getBedAvailabilityAll, getAlos, type Workload } from "../lib/api";

const AX = { color: "#6b7280", fontSize: 10 };

export default function Departments() {
  const [workload, setWorkload] = useState<Workload[]>([]);
  const [avail, setAvail] = useState<any[]>([]);
  const [alos, setAlos] = useState<any[]>([]);

  useEffect(() => {
    getWorkload().then(setWorkload);
    getBedAvailabilityAll(5).then(setAvail);
    getAlos().then(setAlos);
  }, []);

  const alosOption = {
    grid: { left: 90, right: 20, top: 10, bottom: 24 },
    tooltip: { trigger: "axis" },
    xAxis: { type: "value", axisLabel: AX, splitLine: { lineStyle: { color: "#232732" } } },
    yAxis: { type: "category", data: alos.map((a) => a.department_name), axisLabel: AX },
    series: [{
      type: "bar", data: alos.map((a) => a.alos_days),
      itemStyle: { color: "#5ca8ff", borderRadius: [0, 4, 4, 0] }, barWidth: "55%",
    }],
  };

  return (
    <div className="space-y-6">
      <Card title="Department Workload Index — composite stress (occupancy · admissions · nurse load)">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          {workload.map((w, i) => {
            const color = w.status === "critical" ? "#ff5c5c" : w.status === "warning" ? "#ffb545" : "#d4f23a";
            return (
              <motion.div key={w.department_id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }} className="rounded-xl border border-ink-400/50 bg-ink-700/50 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-slate-200">{w.department_name}</span>
                  <StatusBadge status={w.status} />
                </div>
                <div className="mt-3 flex items-end gap-2">
                  <span className="text-3xl font-bold" style={{ color }}>{w.workload_index.toFixed(0)}</span>
                  <span className="mb-1 text-[11px] text-muted">/ 100</span>
                </div>
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-ink-500">
                  <motion.div initial={{ width: 0 }} animate={{ width: `${w.workload_index}%` }}
                    transition={{ duration: 0.7 }} className="h-full rounded-full" style={{ background: color }} />
                </div>
                <div className="mt-3 grid grid-cols-3 gap-1 text-[10px] text-muted">
                  <div><div className="text-slate-300">{(w.occupancy_rate * 100).toFixed(0)}%</div>occ</div>
                  <div><div className="text-slate-300">{w.admissions_today}</div>adm</div>
                  <div><div className="text-slate-300">{w.patients_per_nurse}</div>p/nurse</div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Bed Availability Forecast — when will a shortage hit?">
          <div className="space-y-2 max-h-[340px] overflow-y-auto pr-1">
            {avail.map((a) => (
              <div key={a.department_id} className="rounded-lg border border-ink-400/50 bg-ink-700/40 p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-200">{a.department_name}</span>
                  {a.shortage_expected_on
                    ? <span className="text-xs text-status-critical">shortage ≈ {a.shortage_expected_on.slice(5)}</span>
                    : <span className="text-xs text-status-normal">no shortage in window</span>}
                </div>
                <div className="mt-2 flex gap-1">
                  {a.projection.map((p: any, i: number) => {
                    const c = p.status === "critical" ? "#ff5c5c" : p.status === "warning" ? "#ffb545" : "#43d9a3";
                    return (
                      <div key={i} className="flex-1 text-center" title={`${p.date}: ${(p.projected_occupancy_rate * 100).toFixed(0)}%`}>
                        <div className="h-10 rounded" style={{ background: `${c}33`, border: `1px solid ${c}` }}>
                          <div className="pt-1 text-[9px]" style={{ color: c }}>{(p.projected_occupancy_rate * 100).toFixed(0)}%</div>
                        </div>
                        <div className="mt-1 text-[8px] text-muted">{p.date.slice(5)}</div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Average Length of Stay by Department">
          <ReactECharts option={alosOption} style={{ height: 340 }} notMerge />
        </Card>
      </div>
    </div>
  );
}
