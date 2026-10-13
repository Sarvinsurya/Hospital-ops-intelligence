import { useEffect, useState } from "react";
import ReactECharts from "echarts-for-react";
import { motion } from "framer-motion";
import { Card } from "../components/ui";
import { getWaitingTimes, predictWait, getWaitSensitivity, getWaitModelMeta } from "../lib/api";

const AX = { color: "#6b7280", fontSize: 10 };
const SPLIT = { lineStyle: { color: "#232732" } };
const URG_COLOR: Record<string, string> = { Critical: "#ff5c5c", High: "#ffb545", Medium: "#5ca8ff", Low: "#43d9a3" };

export default function Waiting() {
  const [wt, setWt] = useState<any>(null);
  const [meta, setMeta] = useState<any>(null);
  const [sens, setSens] = useState<any[]>([]);
  // predictor inputs
  const [urgency, setUrgency] = useState("High");
  const [ratio, setRatio] = useState(3);
  const [occ, setOcc] = useState(0.8);
  const [shift, setShift] = useState("Evening");
  const [spec, setSpec] = useState(3);
  const [pred, setPred] = useState<number | null>(null);

  useEffect(() => {
    getWaitingTimes().then(setWt);
    getWaitModelMeta().then(setMeta);
    getWaitSensitivity(urgency, shift).then(setSens);
  }, []);

  useEffect(() => { getWaitSensitivity(urgency, shift).then(setSens); }, [urgency, shift]);

  const runPredict = async () => {
    const r = await predictWait({ urgency, nurse_patient_ratio: ratio, er_occupancy: occ, shift, specialist_availability: spec });
    setPred(r.predicted_wait_min);
  };
  useEffect(() => { runPredict(); /* initial */ }, []);

  const urgencyOption = wt && {
    grid: { left: 50, right: 16, top: 20, bottom: 24 },
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: wt.by_urgency.map((u: any) => u.urgency), axisLabel: AX },
    yAxis: { type: "value", name: "min", axisLabel: AX, splitLine: SPLIT },
    series: [{
      type: "bar", data: wt.by_urgency.map((u: any) => ({ value: u.avg_wait_min, itemStyle: { color: URG_COLOR[u.urgency] } })),
      barWidth: "50%", itemStyle: { borderRadius: [4, 4, 0, 0] },
    }],
  };

  const shiftOption = wt && {
    grid: { left: 50, right: 16, top: 20, bottom: 24 },
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: wt.by_shift.map((s: any) => s.shift), axisLabel: AX },
    yAxis: { type: "value", name: "min", axisLabel: AX, splitLine: SPLIT },
    series: [{
      type: "line", smooth: true, symbol: "circle", symbolSize: 8,
      data: wt.by_shift.map((s: any) => s.avg_wait_min),
      lineStyle: { color: "#d4f23a", width: 3 }, itemStyle: { color: "#d4f23a" },
      areaStyle: { color: "rgba(212,242,58,0.1)" },
    }],
  };

  const sensOption = {
    grid: { left: 50, right: 16, top: 20, bottom: 24 },
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", name: "patients/nurse", data: sens.map((s) => s.nurse_patient_ratio), axisLabel: AX },
    yAxis: { type: "value", name: "min", axisLabel: AX, splitLine: SPLIT },
    series: [{
      type: "line", smooth: true, symbol: "circle", symbolSize: 7,
      data: sens.map((s) => s.predicted_wait_min),
      lineStyle: { color: "#ffb545", width: 3 }, itemStyle: { color: "#ffb545" },
      areaStyle: { color: "rgba(255,181,69,0.1)" },
    }],
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Avg ER Wait by Urgency (real Kaggle ER data)">
          {urgencyOption && <ReactECharts option={urgencyOption} style={{ height: 240 }} notMerge />}
        </Card>
        <Card title="Avg ER Wait by Shift">
          {shiftOption && <ReactECharts option={shiftOption} style={{ height: 240 }} notMerge />}
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* ML Wait Predictor */}
        <Card title={`Wait-Time Predictor · ML (R²=${meta?.r2 ?? "—"}, MAE=${meta?.mae_min ?? "—"}m)`}>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Urgency">
              <select value={urgency} onChange={(e) => setUrgency(e.target.value)} className="inp">
                {["Critical", "High", "Medium", "Low"].map((u) => <option key={u}>{u}</option>)}
              </select>
            </Field>
            <Field label="Shift">
              <select value={shift} onChange={(e) => setShift(e.target.value)} className="inp">
                {["Morning", "Evening", "Night"].map((s) => <option key={s}>{s}</option>)}
              </select>
            </Field>
            <Field label={`Patients / nurse: ${ratio}`}>
              <input type="range" min={1} max={5} step={1} value={ratio} onChange={(e) => setRatio(+e.target.value)} className="w-full accent-lime" />
            </Field>
            <Field label={`ER occupancy: ${(occ * 100).toFixed(0)}%`}>
              <input type="range" min={0.3} max={1} step={0.05} value={occ} onChange={(e) => setOcc(+e.target.value)} className="w-full accent-lime" />
            </Field>
            <Field label={`Specialists: ${spec}`}>
              <input type="range" min={0} max={5} step={1} value={spec} onChange={(e) => setSpec(+e.target.value)} className="w-full accent-lime" />
            </Field>
            <div className="flex items-end">
              <button onClick={runPredict} className="w-full rounded-lg bg-lime py-2 text-sm font-semibold text-ink-900 hover:bg-lime-soft">
                Predict
              </button>
            </div>
          </div>
          <motion.div key={pred ?? 0} initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
            className="mt-4 rounded-xl border border-lime/30 bg-lime/5 p-4 text-center">
            <div className="text-xs uppercase tracking-wide text-muted">Predicted wait</div>
            <div className="text-4xl font-bold text-lime">{pred !== null ? `${pred} min` : "—"}</div>
          </motion.div>
        </Card>

        <Card title="Sensitivity: wait vs nurse ratio (drives staffing advice)">
          <ReactECharts option={sensOption} style={{ height: 300 }} notMerge />
        </Card>
      </div>

      <style>{`.inp{width:100%;background:#14161c;border:1px solid #2d323f;border-radius:8px;padding:7px 10px;font-size:13px;color:#e2e8f0}`}</style>
    </div>
  );
}

function Field({ label, children }: any) {
  return (
    <div>
      <label className="mb-1 block text-[11px] text-muted">{label}</label>
      {children}
    </div>
  );
}
