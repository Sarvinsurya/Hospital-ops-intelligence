import { useEffect, useState } from "react";
import ReactECharts from "echarts-for-react";
import { Card } from "../components/ui";
import { getSankey, getPatientFlow } from "../lib/api";

const AX = { color: "#6b7280", fontSize: 10 };
const SPLIT = { lineStyle: { color: "#232732" } };

export default function Flow() {
  const [sankey, setSankey] = useState<any>(null);
  const [flow, setFlow] = useState<any[]>([]);

  useEffect(() => {
    getSankey().then(setSankey);
    getPatientFlow(14).then(setFlow);
  }, []);

  const sankeyOption = sankey && {
    tooltip: { trigger: "item", triggerOn: "mousemove" },
    series: [{
      type: "sankey",
      data: sankey.nodes.map((n: any) => ({ name: n.name })),
      links: sankey.links,
      emphasis: { focus: "adjacency" },
      lineStyle: { color: "gradient", curveness: 0.5, opacity: 0.4 },
      label: { color: "#cbd5e1", fontSize: 11 },
      nodeAlign: "left",
      itemStyle: { color: "#d4f23a", borderColor: "#0e0f13" },
      levels: [
        { depth: 0, itemStyle: { color: "#5ca8ff" } },
        { depth: 1, itemStyle: { color: "#d4f23a" } },
        { depth: 2, itemStyle: { color: "#43d9a3" } },
      ],
    }],
  };

  const flowOption = {
    grid: { left: 40, right: 16, top: 24, bottom: 24 },
    tooltip: { trigger: "axis" },
    legend: { data: ["Arrivals", "Transfers", "Discharges"], textStyle: { color: "#8b92a3" }, top: 0 },
    xAxis: { type: "category", data: flow.map((f) => f.date.slice(5)), axisLabel: AX },
    yAxis: { type: "value", axisLabel: AX, splitLine: SPLIT },
    series: [
      { name: "Arrivals", type: "line", smooth: true, symbol: "none", data: flow.map((f) => f.arrivals), lineStyle: { color: "#5ca8ff", width: 2 } },
      { name: "Discharges", type: "line", smooth: true, symbol: "none", data: flow.map((f) => f.discharges), lineStyle: { color: "#43d9a3", width: 2 } },
      { name: "Transfers", type: "bar", data: flow.map((f) => f.transfers), itemStyle: { color: "#ffb54588", borderRadius: [3, 3, 0, 0] }, barWidth: "40%" },
    ],
  };

  return (
    <div className="space-y-6">
      <Card title="Patient Flow Sankey — Arrivals → Departments → Transfer / Discharge">
        {sankeyOption && <ReactECharts option={sankeyOption} style={{ height: 420 }} notMerge />}
      </Card>
      <Card title="Patient Flow (14d) — arrivals, transfers, discharges">
        <ReactECharts option={flowOption} style={{ height: 280 }} notMerge />
      </Card>
    </div>
  );
}
