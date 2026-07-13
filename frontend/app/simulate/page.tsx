"use client";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { api, usd, ms, runToCompletion } from "../../lib/api";
import { Transcript, ScoreCard } from "../../components/Transcript";

function SimInner() {
  const params = useSearchParams();
  const [agents, setAgents] = useState<any[]>([]);
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [meta, setMeta] = useState<any>(null);
  const [agentId, setAgentId] = useState(params.get("agent") || "");
  const [scenarioId, setScenarioId] = useState(params.get("scenario") || "");
  const [maxTurns, setMaxTurns] = useState(6);
  const [running, setRunning] = useState(false);
  const [phase, setPhase] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.agents().then(setAgents).catch(() => {});
    api.scenarios().then(setScenarios).catch(() => {});
    api.meta().then(setMeta).catch(() => {});
  }, []);

  const agent = agents.find((a) => a.id === agentId);
  const scenario = scenarios.find((s) => s.id === scenarioId);
  const cap = meta?.max_turns_cap || 12;

  async function run() {
    if (!agentId || !scenarioId) return;
    setRunning(true); setErr(null); setResult(null); setPhase("queued");
    try {
      const r = await runToCompletion(
        () => api.simulate({ agent_id: agentId, scenario_id: scenarioId, max_turns: maxTurns }),
        (rid) => api.getRun(rid),
        (s) => setPhase(s),
      );
      setResult(r);
    } catch (e: any) { setErr(e.message || "simulation failed"); }
    finally { setRunning(false); setPhase(null); }
  }

  return (
    <div className="py-8">
      <h1 className="text-[22px] font-semibold">Run a simulation</h1>
      <p className="mt-1 text-[13px] text-dim">Pick an agent and a caller scenario. Both sides speak through the live relay for up to {cap} turns, then the transcript is judged.</p>

      {meta && !meta.relay_available && (
        <div className="mt-4 rounded-xl border border-warn/30 bg-warn/5 px-4 py-2.5 text-[12.5px] text-warn">
          Relay key not configured — real simulations are unavailable until <code className="text-ink">NYQUEST_API_KEY</code> is set on the server.
        </div>
      )}

      <div className="mt-5 rounded-2xl border border-line bg-panel p-5">
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="block"><span className="text-[12px] text-dim">Agent</span>
              <select value={agentId} onChange={(e) => setAgentId(e.target.value)} className={inp}>
                <option value="">Select an agent…</option>
                {agents.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
              </select></label>
            {agent && (
              <div className="mt-2 rounded-lg border border-line bg-panel2 p-3 text-[12px] text-dim">
                {agent.goal && <p><span className="text-faint">Goal:</span> {agent.goal}</p>}
                {agent.guardrails && <p className="mt-1"><span className="text-faint">Guardrails:</span> {agent.guardrails}</p>}
              </div>
            )}
            {!agents.length && <p className="mt-2 text-[12px] text-faint">No agents — <Link href="/agents" className="text-cy hover:underline">design one</Link>.</p>}
          </div>
          <div>
            <label className="block"><span className="text-[12px] text-dim">Scenario</span>
              <select value={scenarioId} onChange={(e) => setScenarioId(e.target.value)} className={inp}>
                <option value="">Select a scenario…</option>
                {scenarios.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select></label>
            {scenario && (
              <div className="mt-2 rounded-lg border border-line bg-panel2 p-3 text-[12px] text-dim">
                {scenario.caller_persona && <p><span className="text-faint">Caller:</span> {scenario.caller_persona}</p>}
                {scenario.objective && <p className="mt-1"><span className="text-faint">Wants:</span> {scenario.objective}</p>}
              </div>
            )}
            {!scenarios.length && <p className="mt-2 text-[12px] text-faint">No scenarios — <Link href="/scenarios" className="text-cy hover:underline">create one</Link>.</p>}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-2 text-[12.5px] text-dim">
            Max turns
            <input type="range" min={2} max={cap} value={maxTurns} onChange={(e) => setMaxTurns(Number(e.target.value))} className="accent-vi" />
            <span className="tnum w-6 text-ink">{maxTurns}</span>
          </label>
          <button onClick={run} disabled={running || !agentId || !scenarioId}
            className="ml-auto rounded-lg bg-vi px-5 py-2.5 text-[13px] font-semibold text-black hover:opacity-90 disabled:opacity-40">
            {running ? (phase === "running" ? "Simulating the call…" : phase === "queued" ? "Queued…" : "Working…") : "Run simulation →"}
          </button>
        </div>
        {err && <div className="mt-3 rounded-lg border border-bad/30 bg-bad/5 px-3 py-2 text-[12.5px] text-bad">{err}</div>}
      </div>

      {result && (
        <div className="mt-6 grid gap-4 lg:grid-cols-[1.1fr_1fr]">
          <div className="rounded-2xl border border-line bg-panel p-5">
            <div className="mb-3 flex flex-wrap items-center gap-2 text-[12px] text-dim">
              <span className="text-[12px] uppercase tracking-wider text-faint">Transcript</span>
              {result.cost_usd != null && <span>· {usd(result.cost_usd)}</span>}
              {result.latency_ms != null && <span>· {ms(result.latency_ms)}</span>}
              {result.total_tokens != null && <span>· {result.total_tokens} tok</span>}
            </div>
            {result.status === "failed"
              ? <div className="rounded-lg border border-bad/30 bg-bad/5 p-3 text-[12.5px] text-bad">{result.error}</div>
              : <Transcript turns={result.transcript || []} />}
          </div>
          <div className="space-y-4">
            <ScoreCard scores={result.scores} outcome={result.outcome} />
            <div className="text-[12px]"><Link href={`/runs/${result.id}`} className="text-cy hover:underline">Open full run →</Link></div>
          </div>
        </div>
      )}
    </div>
  );
}

const inp = "mt-1 w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-[13px] text-ink outline-none focus:border-vi/50";

export default function SimulatePage() {
  return <Suspense fallback={<div className="py-8 text-[13px] text-dim">Loading…</div>}><SimInner /></Suspense>;
}
