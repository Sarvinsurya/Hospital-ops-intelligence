import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight, Check, X } from "lucide-react";
import { Card } from "../components/ui";
import { getOccupancyByDept, simulateReallocation, type DeptOccupancy } from "../lib/api";

export default function Simulator() {
  const [depts, setDepts] = useState<DeptOccupancy[]>([]);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [patients, setPatients] = useState(3);
  const [result, setResult] = useState<any>(null);

  useEffect(() => {
    getOccupancyByDept().then((d) => {
      setDepts(d);
      const full = d.find((x) => x.occupancy_rate >= 0.9) ?? d[0];
      const spare = [...d].sort((a, b) => a.occupancy_rate - b.occupancy_rate)[0];
      setFrom(full.department_name);
      setTo(spare.department_name);
    });
  }, []);

  const run = async () => {
    const r = await simulateReallocation(from, to, patients);
    setResult(r);
  };

  return (
    <div className="space-y-6">
      <Card title="Bed Reallocation Simulator — model a patient transfer before you commit">
        <div className="grid grid-cols-1 items-end gap-4 md:grid-cols-4">
          <Sel label="From (overcrowded)" value={from} onChange={setFrom} depts={depts} />
          <Sel label="To (spare capacity)" value={to} onChange={setTo} depts={depts} />
          <div>
            <label className="mb-1 block text-[11px] text-muted">Patients to move: {patients}</label>
            <input type="range" min={1} max={15} value={patients} onChange={(e) => setPatients(+e.target.value)} className="w-full accent-lime" />
          </div>
          <button onClick={run} className="rounded-lg bg-lime py-2.5 text-sm font-semibold text-ink-900 hover:bg-lime-soft">
            Simulate
          </button>
        </div>
      </Card>

      {result && !result.error && (
        <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }}>
          <Card title="Simulation Result">
            <div className="flex flex-col items-stretch gap-4 md:flex-row md:items-center">
              <BeforeAfter title={result.from.department} before={result.from.before_rate} after={result.from.after_rate} good={false} />
              <div className="flex flex-col items-center justify-center text-muted">
                <ArrowRight size={28} className="text-lime" />
                <span className="text-xs">{result.patients_requested} patients</span>
              </div>
              <BeforeAfter title={result.to.department} before={result.to.before_rate} after={result.to.after_rate} good />
            </div>
            <div className={`mt-5 flex items-center gap-2 rounded-xl border p-3 ${result.feasible ? "border-status-normal/40 bg-status-normal/10" : "border-status-critical/40 bg-status-critical/10"}`}>
              {result.feasible ? <Check className="text-status-normal" size={18} /> : <X className="text-status-critical" size={18} />}
              <span className={`text-sm ${result.feasible ? "text-status-normal" : "text-status-critical"}`}>
                {result.feasible ? "Feasible" : "Not feasible"} — {result.note}. Destination spare capacity: {result.to.spare_capacity} beds.
              </span>
            </div>
          </Card>
        </motion.div>
      )}
      {result?.error && <Card><p className="text-sm text-status-critical">{result.error}</p></Card>}
    </div>
  );
}

function Sel({ label, value, onChange, depts }: any) {
  return (
    <div>
      <label className="mb-1 block text-[11px] text-muted">{label}</label>
      <select value={value} onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-ink-400 bg-ink-700 px-3 py-2 text-sm text-slate-200">
        {depts.map((d: DeptOccupancy) => (
          <option key={d.department_id} value={d.department_name}>
            {d.department_name} ({(d.occupancy_rate * 100).toFixed(0)}%)
          </option>
        ))}
      </select>
    </div>
  );
}

function BeforeAfter({ title, before, after, good }: { title: string; before: number; after: number; good: boolean }) {
  const bc = (v: number) => (v >= 0.9 ? "#ff5c5c" : v >= 0.8 ? "#ffb545" : "#43d9a3");
  return (
    <div className="flex-1 rounded-xl border border-ink-400/50 bg-ink-700/40 p-4">
      <div className="mb-3 text-sm font-semibold text-slate-200">{title}</div>
      <div className="flex items-center gap-3">
        {[["before", before], ["after", after]].map(([lbl, v]: any) => (
          <div key={lbl} className="flex-1 text-center">
            <div className="text-[10px] uppercase text-muted">{lbl}</div>
            <motion.div key={v} initial={{ scale: 0.8 }} animate={{ scale: 1 }}
              className="text-2xl font-bold" style={{ color: bc(v) }}>{(v * 100).toFixed(0)}%</motion.div>
            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-ink-500">
              <div className="h-full rounded-full" style={{ width: `${v * 100}%`, background: bc(v) }} />
            </div>
          </div>
        ))}
      </div>
      <div className="mt-2 text-center text-[11px]" style={{ color: good ? "#43d9a3" : "#ffb545" }}>
        {good ? "receives load" : "relieved"}
      </div>
    </div>
  );
}
