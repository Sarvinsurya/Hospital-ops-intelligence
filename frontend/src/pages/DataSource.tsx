import { useEffect, useState } from "react";
import { Database, CheckCircle2 } from "lucide-react";
import { Card } from "../components/ui";
import { getDataSource, getDepartments } from "../lib/api";

export default function DataSource() {
  const [src, setSrc] = useState<any>(null);
  const [depts, setDepts] = useState<any[]>([]);

  useEffect(() => {
    getDataSource().then(setSrc);
    getDepartments().then(setDepts);
  }, []);

  return (
    <div className="space-y-6">
      <Card title="Data Provenance — real Kaggle data vs calibrated operational backbone">
        <div className="mb-4 flex items-center gap-2 text-status-normal">
          <CheckCircle2 size={18} />
          <span className="text-sm">Real Kaggle data: {src?.real_data_available ? "loaded" : "not found"}</span>
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Source title="ER Wait Time" tag="Kaggle · real"
            desc="5,000 real ER visits. Drives all waiting-time KPIs and trains the wait-time ML model (R²=0.80)."
            rows={src?.row_counts?.fact_er_visits} accent="#43d9a3" />
          <Source title="Hospital Beds Management" tag="Kaggle · real"
            desc="Weekly service bed data + 1,000 real patient stays + staff schedules."
            rows={(src?.row_counts?.fact_services_weekly ?? 0) + (src?.row_counts?.fact_patients_real ?? 0)} accent="#5ca8ff" />
          <Source title="Operational Backbone" tag="synthetic · calibrated"
            desc="Daily admissions/occupancy/staffing calibrated to the real services (beds, ALOS) for the live control room."
            rows={src?.row_counts?.fact_admissions} accent="#d4f23a" />
        </div>
      </Card>

      <Card title="Departments">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-[11px] uppercase text-muted">
              <tr className="border-b border-ink-400/50">
                <th className="py-2">Department</th><th>Beds</th><th>Target Occ</th><th>ALOS</th><th>Adm/day</th><th>Wing</th>
              </tr>
            </thead>
            <tbody>
              {depts.map((d) => (
                <tr key={d.department_id} className="border-b border-ink-400/20">
                  <td className="py-2 font-medium text-slate-200">{d.department_name}</td>
                  <td>{d.total_beds}</td>
                  <td>{(d.target_occupancy * 100).toFixed(0)}%</td>
                  <td>{d.avg_length_of_stay}d</td>
                  <td>{d.adm_per_day}</td>
                  <td className="text-muted">{d.facility_wing}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function Source({ title, tag, desc, rows, accent }: any) {
  return (
    <div className="rounded-xl border border-ink-400/50 bg-ink-700/40 p-4">
      <div className="flex items-center gap-2">
        <Database size={16} style={{ color: accent }} />
        <span className="text-sm font-semibold text-slate-200">{title}</span>
      </div>
      <span className="mt-1 inline-block rounded-full px-2 py-0.5 text-[10px] font-medium"
        style={{ color: accent, background: `${accent}1a`, border: `1px solid ${accent}44` }}>{tag}</span>
      <p className="mt-2 text-xs text-muted">{desc}</p>
      <div className="mt-3 text-2xl font-bold" style={{ color: accent }}>{rows?.toLocaleString() ?? "—"}</div>
      <div className="text-[11px] text-muted">rows</div>
    </div>
  );
}
