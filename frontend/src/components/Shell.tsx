import { NavLink, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import {
  LayoutDashboard, Activity, Clock, Users, GitBranch,
  Shuffle, Bot, Plus, Database,
} from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { getAgentHealth, getSummary } from "../lib/api";
import { KpiPill } from "./ui";

const nav = [
  { to: "/", icon: LayoutDashboard, label: "Overview" },
  { to: "/departments", icon: Activity, label: "Departments" },
  { to: "/waiting", icon: Clock, label: "Waiting Times" },
  { to: "/staffing", icon: Users, label: "Staffing" },
  { to: "/flow", icon: GitBranch, label: "Patient Flow" },
  { to: "/simulator", icon: Shuffle, label: "Reallocation" },
  { to: "/agent", icon: Bot, label: "AI War Room" },
  { to: "/source", icon: Database, label: "Data Source" },
];

export default function Shell({ children }: { children: ReactNode }) {
  const loc = useLocation();
  const [agentOk, setAgentOk] = useState(false);
  const [summary, setSummary] = useState<any>(null);

  useEffect(() => {
    getAgentHealth().then((h) => setAgentOk(h.connected)).catch(() => setAgentOk(false));
    getSummary().then(setSummary).catch(() => {});
    const t = setInterval(() => getSummary().then(setSummary).catch(() => {}), 30000);
    return () => clearInterval(t);
  }, []);

  const current = nav.find((n) => n.to === loc.pathname)?.label ?? "Overview";

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Icon rail */}
      <aside className="flex w-16 flex-col items-center gap-2 border-r border-ink-400/50 bg-ink-900/80 py-4">
        <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-lime text-ink-900">
          <Plus size={22} strokeWidth={3} />
        </div>
        {nav.map((n) => (
          <NavLink key={n.to} to={n.to} title={n.label}
            className={({ isActive }) => `rail-btn ${isActive ? "rail-btn-active" : ""}`}>
            <n.icon size={19} />
          </NavLink>
        ))}
      </aside>

      {/* Main */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Topbar */}
        <header className="flex items-center justify-between border-b border-ink-400/50 bg-ink-900/60 px-6 py-3 backdrop-blur">
          <div>
            <h1 className="text-lg font-bold text-slate-100">{current}</h1>
            <p className="text-[11px] text-muted">
              Hospital Operations Intelligence · real-time control room
            </p>
          </div>
          <div className="flex items-center gap-2">
            {summary && (
              <>
                <KpiPill label="Occupancy" value={`${(summary.occupancy.occupancy_rate * 100).toFixed(0)}%`} status={summary.occupancy.status} />
                <KpiPill label="Avg Wait" value={`${summary.waiting_time.avg_wait_min}m`} status={summary.waiting_time.status} />
                <KpiPill label="Admissions" value={`${summary.admissions_today}`} status="info" />
                <KpiPill label="Emergency" value={`${(summary.emergency_share * 100).toFixed(0)}%`} status="normal" />
              </>
            )}
            <div className="pill">
              <motion.span
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ repeat: Infinity, duration: 2 }}
                className="h-2 w-2 rounded-full"
                style={{ background: agentOk ? "#43d9a3" : "#ff5c5c" }}
              />
              <span className="text-muted">Agent</span>
              <span className="font-semibold text-slate-100">{agentOk ? "online" : "offline"}</span>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto bg-grid-faint bg-[size:32px_32px] p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
