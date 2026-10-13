import type { ReactNode } from "react";
import { motion } from "framer-motion";

export const statusColor: Record<string, string> = {
  critical: "#ff5c5c",
  warning: "#ffb545",
  normal: "#43d9a3",
  danger: "#ff5c5c",
  ok: "#43d9a3",
  info: "#5ca8ff",
};

export function Card({ children, className = "", title, action }: {
  children: ReactNode; className?: string; title?: string; action?: ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className={`glass-card p-5 ${className}`}
    >
      {(title || action) && (
        <div className="mb-4 flex items-center justify-between">
          {title && <h3 className="text-sm font-semibold tracking-wide text-slate-300">{title}</h3>}
          {action}
        </div>
      )}
      {children}
    </motion.div>
  );
}

export function KpiPill({ label, value, status = "normal", icon }: {
  label: string; value: string; status?: string; icon?: ReactNode;
}) {
  const color = statusColor[status] ?? "#8b92a3";
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="pill"
    >
      <span className="h-2 w-2 rounded-full" style={{ background: color, boxShadow: `0 0 8px ${color}` }} />
      {icon}
      <span className="text-muted">{label}</span>
      <span className="font-semibold text-slate-100">{value}</span>
    </motion.div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const color = statusColor[status] ?? "#8b92a3";
  return (
    <span
      className="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider"
      style={{ color, background: `${color}1a`, border: `1px solid ${color}55` }}
    >
      {status}
    </span>
  );
}
