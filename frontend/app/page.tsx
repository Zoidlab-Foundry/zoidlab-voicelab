"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, usd, num } from "../lib/api";

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-2xl border border-line bg-panel p-4">
      <div className="text-[11px] uppercase tracking-wider text-faint">{label}</div>
      <div className="mt-1.5 text-[24px] font-semibold tnum text-ink">{value}</div>
      {sub && <div className="mt-0.5 text-[12px] text-dim">{sub}</div>}
    </div>
  );
}

const OUTCOME_STYLE: Record<string, string> = {
  success: "bg-ok/10 text-ok", partial: "bg-warn/10 text-warn",
  goal_missed: "bg-warn/10 text-warn", guardrail_violation: "bg-bad/10 text-bad",
  blocked: "bg-warn/10 text-warn",
};

export default function Dashboard() {
  const [s, setS] = useState<any>(null);
  const [runs, setRuns] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [meta, setMeta] = useState<any>(null);

  useEffect(() => {
    api.stats().then(setS).catch(() => {});
    api.runs().then((r) => setRuns(r.slice(0, 6))).catch(() => {});
    api.agents().then(setAgents).catch(() => {});
    api.meta().then(setMeta).catch(() => {});
  }, []);

  return (
    <div className="relative py-8">
      <div className="hero-glow" />
      <div className="relative flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[26px] font-semibold tracking-tight">
            Design the agent. <span className="prism-text">Hear the call.</span>
          </h1>
          <p className="mt-1.5 max-w-2xl text-[13px] leading-relaxed text-dim">
            Build a voice agent — persona, goal, guardrails — then put it on a real simulated call
            against a caller scenario. Every turn is a genuine relay completion; every transcript is
            scored by an LLM judge for goal completion and guardrail adherence.
          </p>
        </div>
        <Link href="/simulate" className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-black hover:opacity-90">
          Run a simulation →
        </Link>
      </div>

      {meta && (
        <div className={`relative mt-4 flex flex-wrap items-center gap-2 rounded-xl border px-4 py-2.5 text-[12.5px] ${meta.relay_available ? "border-ok/30 bg-ok/5 text-ok" : "border-warn/30 bg-warn/5 text-warn"}`}>
          <span className={`h-2 w-2 rounded-full ${meta.relay_available ? "bg-ok" : "bg-warn"}`} />
          {meta.relay_available
            ? <>Live relay connected — simulations bill the <b>{meta.billing_mode}</b> wallet. Transport today: <code className="text-ink">text simulation</code> (streaming audio / telephony planned).</>
            : <>Relay key not configured — real simulations are unavailable until <code className="text-ink">NYQUEST_API_KEY</code> is set.</>}
        </div>
      )}

      <div className="relative mt-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Voice agents" value={num(s?.agents ?? 0)} sub="designed" />
        <Stat label="Scenarios" value={num(s?.scenarios ?? 0)} sub="caller test cases" />
        <Stat label="Simulations" value={num(s?.runs ?? 0)} sub="real calls run" />
        <Stat label="Spend" value={usd(s?.spend_usd ?? 0)} sub={`${num(s?.successes ?? 0)} successful`} />
      </div>

      <div className="relative mt-4 grid gap-4 lg:grid-cols-[1fr_1fr]">
        <div className="rounded-2xl border border-line bg-panel p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-[14px] font-semibold">Voice agents</h2>
            <Link href="/agents" className="text-[12px] text-cy hover:underline">All →</Link>
          </div>
          <div className="mt-3 space-y-2">
            {agents.slice(0, 6).map((a) => (
              <Link key={a.id} href={`/simulate?agent=${a.id}`} className="block rounded-lg border border-line bg-panel2 p-2.5 hover:border-vi/40">
                <div className="flex items-center justify-between">
                  <div className="text-[12.5px] font-medium text-ink">{a.name}</div>
                  <span className="rounded-full bg-vi/10 px-2 py-0.5 text-[10.5px] text-vi">{a.voice}</span>
                </div>
                <div className="mt-0.5 line-clamp-1 text-[11px] text-faint">{a.goal || a.description}</div>
              </Link>
            ))}
            {!agents.length && <p className="text-[12px] text-faint">No agents yet. <Link href="/agents" className="text-cy hover:underline">Design one</Link>.</p>}
          </div>
        </div>
        <div className="rounded-2xl border border-line bg-panel p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-[14px] font-semibold">Recent simulations</h2>
            <Link href="/runs" className="text-[12px] text-cy hover:underline">All →</Link>
          </div>
          <div className="mt-3 space-y-2">
            {runs.map((r) => (
              <Link key={r.id} href={`/runs/${r.id}`} className="block rounded-lg border border-line bg-panel2 p-2.5 hover:border-vi/40">
                <div className="flex items-center justify-between">
                  <div className="text-[12.5px] font-medium text-ink">{r.agent_name}</div>
                  <span className={`rounded-full px-2 py-0.5 text-[10.5px] ${OUTCOME_STYLE[r.outcome] || "bg-warn/10 text-warn"}`}>{r.outcome || r.status}</span>
                </div>
                <div className="mt-0.5 text-[11px] text-faint">vs {r.scenario_name} · {r.turns_used ?? "—"} turns</div>
              </Link>
            ))}
            {!runs.length && <p className="text-[12px] text-faint">No simulations yet. <Link href="/simulate" className="text-cy hover:underline">Run one</Link>.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
