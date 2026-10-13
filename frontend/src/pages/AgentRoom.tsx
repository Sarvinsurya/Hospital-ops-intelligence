import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bot, Zap, Loader2, Wrench, Send } from "lucide-react";
import { Card, StatusBadge } from "../components/ui";
import {
  investigate, autoInvestigate, getTriggers, getIncidents,
  type Investigation, type Incident,
} from "../lib/api";

const SUGGESTIONS = [
  "Which department is most overcrowded and what should we do?",
  "ER wait times are high — what is the root cause?",
  "Where are the staffing danger zones tonight?",
  "Is a bed shortage expected in the next 5 days?",
];

export default function AgentRoom() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Investigation | null>(null);
  const [triggers, setTriggers] = useState<any[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);

  const refresh = () => {
    getTriggers().then((t) => setTriggers(t.anomalies));
    getIncidents(20).then(setIncidents);
  };
  useEffect(refresh, []);

  const run = async (q: string) => {
    if (!q.trim()) return;
    setLoading(true); setResult(null);
    try {
      const r = await investigate(q);
      setResult(r);
      refresh();
    } finally { setLoading(false); }
  };

  const runAuto = async () => {
    setLoading(true); setResult(null);
    try {
      const r = await autoInvestigate();
      setResult(r.investigation ?? { answer: r.message, tools_used: [], trace: [], error: null });
      refresh();
    } finally { setLoading(false); }
  };

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      {/* Left: investigation */}
      <div className="space-y-6 lg:col-span-2">
        <Card title="AI Investigation Agent · qwen2.5:3b (local)">
          <div className="flex gap-2">
            <input value={query} onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && run(query)}
              placeholder="Ask the agent to investigate an operational problem…"
              className="flex-1 rounded-lg border border-ink-400 bg-ink-700 px-4 py-2.5 text-sm text-slate-200 outline-none focus:border-lime/50" />
            <button onClick={() => run(query)} disabled={loading}
              className="flex items-center gap-1.5 rounded-lg bg-lime px-4 text-sm font-semibold text-ink-900 hover:bg-lime-soft disabled:opacity-50">
              <Send size={15} /> Investigate
            </button>
            <button onClick={runAuto} disabled={loading} title="Auto-investigate top anomaly"
              className="flex items-center gap-1.5 rounded-lg border border-lime/40 px-3 text-sm font-semibold text-lime hover:bg-lime/10 disabled:opacity-50">
              <Zap size={15} /> Auto
            </button>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button key={s} onClick={() => { setQuery(s); run(s); }}
                className="rounded-full border border-ink-400/60 bg-ink-700/60 px-3 py-1 text-[11px] text-muted hover:border-lime/40 hover:text-lime">
                {s}
              </button>
            ))}
          </div>

          <AnimatePresence mode="wait">
            {loading && (
              <motion.div key="load" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="mt-5 flex items-center gap-2 text-sm text-muted">
                <Loader2 className="animate-spin text-lime" size={18} /> Agent is investigating — calling tools, gathering evidence…
              </motion.div>
            )}
            {result && !loading && (
              <motion.div key="res" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                className="mt-5 space-y-4">
                {result.error ? (
                  <p className="text-sm text-status-critical">{result.error}</p>
                ) : (
                  <>
                    <div className="rounded-xl border border-ink-400/50 bg-ink-700/40 p-4">
                      <div className="mb-2 flex items-center gap-2 text-lime"><Bot size={16} /><span className="text-xs font-semibold uppercase tracking-wide">Agent Report</span></div>
                      <div className="prose-report text-sm leading-relaxed text-slate-200" dangerouslySetInnerHTML={{ __html: formatReport(result.answer) }} />
                    </div>
                    {result.trace.length > 0 && (
                      <div className="rounded-xl border border-ink-400/50 bg-ink-700/30 p-4">
                        <div className="mb-2 flex items-center gap-2 text-muted"><Wrench size={14} /><span className="text-xs font-semibold uppercase tracking-wide">Explainability · tool trace ({result.trace.length})</span></div>
                        <div className="space-y-1.5">
                          {result.trace.map((t, i) => (
                            <div key={i} className="rounded-lg bg-ink-800/60 p-2 font-mono text-[11px]">
                              <span className="text-lime">{t.tool}</span>
                              <span className="text-muted">({JSON.stringify(t.arguments)})</span>
                              <div className="mt-0.5 truncate text-slate-500">{t.result_preview}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </Card>
      </div>

      {/* Right: triggers + incident history */}
      <div className="space-y-6">
        <Card title={`Active Triggers (${triggers.length})`}>
          <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
            {triggers.length === 0 && <p className="text-sm text-muted">No triggers.</p>}
            {triggers.map((t, i) => (
              <div key={i} className="rounded-lg border border-ink-400/50 bg-ink-700/40 p-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase text-muted">{t.type.replace(/_/g, " ")}</span>
                  <StatusBadge status={t.severity} />
                </div>
                <p className="text-xs text-slate-300">{t.message}</p>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Incident History">
          <div className="space-y-2 max-h-[320px] overflow-y-auto pr-1">
            {incidents.length === 0 && <p className="text-sm text-muted">No incidents logged yet.</p>}
            {incidents.map((inc) => (
              <div key={inc.id} className="rounded-lg border border-ink-400/50 bg-ink-700/40 p-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-muted">{inc.created_at.slice(5, 16).replace("T", " ")}</span>
                  <StatusBadge status={inc.severity} />
                </div>
                <p className="mt-0.5 text-xs text-slate-300">{inc.title}</p>
                <p className="text-[10px] text-muted">{inc.tools_used.length} tools · {inc.trigger_type}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

function formatReport(md: string): string {
  return md
    .replace(/\*\*(.+?)\*\*/g, '<strong class="text-lime">$1</strong>')
    .replace(/\n/g, "<br/>");
}
