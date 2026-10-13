import { useEffect, useState } from "react";
import ReactECharts from "echarts-for-react";
import { Card } from "../components/ui";
import { getStaffing } from "../lib/api";

const SHIFTS = ["Morning", "Evening", "Night"];

export default function Staffing() {
  const [rows, setRows] = useState<any[]>([]);
  useEffect(() => { getStaffing().then(setRows); }, []);

  const depts = Array.from(new Set(rows.map((r) => r.department_name)));
  const data: any[] = [];
  rows.forEach((r) => {
    const x = SHIFTS.indexOf(r.shift);
    const y = depts.indexOf(r.department_name);
    if (x >= 0 && y >= 0) data.push([x, y, r.patients_per_nurse]);
  });

  const maxVal = Math.max(8, ...rows.map((r) => r.patients_per_nurse));

  const option = {
    tooltip: {
      formatter: (p: any) => `${depts[p.data[1]]} · ${SHIFTS[p.data[0]]}<br/>${p.data[2]} patients/nurse`,
    },
    grid: { left: 120, right: 20, top: 20, bottom: 40 },
    xAxis: { type: "category", data: SHIFTS, axisLabel: { color: "#8b92a3" }, splitArea: { show: true } },
    yAxis: { type: "category", data: depts, axisLabel: { color: "#8b92a3", fontSize: 11 }, splitArea: { show: true } },
    visualMap: {
      min: 0, max: maxVal, calculable: true, orient: "horizontal", left: "center", bottom: 0,
      inRange: { color: ["#43d9a3", "#d4f23a", "#ffb545", "#ff5c5c"] },
      textStyle: { color: "#8b92a3" },
    },
    series: [{
      type: "heatmap", data,
      label: { show: true, color: "#0b0c0f", fontWeight: 600, fontSize: 11 },
      itemStyle: { borderColor: "#0e0f13", borderWidth: 2, borderRadius: 4 },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: "rgba(0,0,0,0.5)" } },
    }],
  };

  const dangerZones = rows.filter((r) => r.status === "danger");

  return (
    <div className="space-y-6">
      <Card title="Staff Shift-Gap Heatmap — nurse-to-patient ratio by department × shift">
        <ReactECharts option={option} style={{ height: 420 }} notMerge />
        <p className="mt-2 text-xs text-muted">
          Red cells exceed the safe nurse-to-patient threshold. Night shifts in high-occupancy wards are the usual danger zones.
        </p>
      </Card>

      <Card title={`Danger Zones (${dangerZones.length}) — understaffed shifts needing action`}>
        <div className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-3">
          {dangerZones.length === 0 && <p className="text-sm text-muted">No danger zones.</p>}
          {dangerZones.map((d, i) => (
            <div key={i} className="rounded-lg border border-status-critical/40 bg-status-critical/10 p-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-200">{d.department_name}</span>
                <span className="text-xs text-status-critical">{d.shift}</span>
              </div>
              <div className="mt-1 text-2xl font-bold text-status-critical">{d.patients_per_nurse}</div>
              <div className="text-[11px] text-muted">patients/nurse · {d.nurses_on_duty} nurses on duty</div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
