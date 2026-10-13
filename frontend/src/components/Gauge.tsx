import ReactECharts from "echarts-for-react";

interface GaugeProps {
  value: number;        // 0-100
  label: string;
  suffix?: string;
  thresholds?: { warning: number; critical: number };
}

export default function Gauge({ value, label, suffix = "%", thresholds = { warning: 80, critical: 90 } }: GaugeProps) {
  const color =
    value >= thresholds.critical ? "#ff5c5c" : value >= thresholds.warning ? "#ffb545" : "#d4f23a";

  const option = {
    series: [
      {
        type: "gauge",
        startAngle: 210,
        endAngle: -30,
        min: 0,
        max: 100,
        splitNumber: 5,
        progress: { show: true, width: 12, itemStyle: { color } },
        axisLine: { lineStyle: { width: 12, color: [[1, "#2d323f"]] } },
        axisTick: { show: false },
        splitLine: { length: 10, lineStyle: { color: "#3a4150", width: 1 } },
        axisLabel: { color: "#6b7280", fontSize: 9, distance: 14 },
        pointer: { width: 4, length: "62%", itemStyle: { color } },
        anchor: { show: true, size: 10, itemStyle: { color } },
        detail: {
          valueAnimation: true,
          fontSize: 26,
          fontWeight: 700,
          color: "#f1f5f9",
          offsetCenter: [0, "34%"],
          formatter: (v: number) => `${v.toFixed(0)}${suffix}`,
        },
        title: { show: false },
        data: [{ value }],
      },
    ],
  };

  return (
    <div className="flex flex-col items-center">
      <ReactECharts option={option} style={{ height: 160, width: "100%" }} notMerge lazyUpdate />
      <div className="-mt-3 text-xs font-medium uppercase tracking-wider text-muted">{label}</div>
    </div>
  );
}
