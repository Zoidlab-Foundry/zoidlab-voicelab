"use client";
import { pct } from "../lib/api";

const OUTCOME_LABEL: Record<string, string> = {
  success: "Goal achieved · guardrails held",
  partial: "Partial / inconclusive",
  goal_missed: "Goal missed",
  guardrail_violation: "Guardrail violation",
  blocked: "Blocked by policy",
};

export function ScoreCard({ scores, outcome }: { scores: any; outcome?: string }) {
  if (!scores) return null;
  const chip = (ok: any, label: string) => (
    <span className={`rounded-full px-2.5 py-1 text-[11.5px] font-medium ${ok === true ? "bg-ok/10 text-ok" : ok === false ? "bg-bad/10 text-bad" : "bg-panel2 text-dim"}`}>
      {label}: {ok === true ? "yes" : ok === false ? "no" : "—"}
    </span>
  );
  return (
    <div className="rounded-2xl border border-line bg-panel p-5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[12px] uppercase tracking-wider text-faint">Judge verdict</span>
        {outcome && <span className="text-[12px] text-dim">· {OUTCOME_LABEL[outcome] || outcome}</span>}
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {chip(scores.goal_achieved, "Goal achieved")}
        {chip(scores.guardrail_ok, "Guardrails")}
        {scores.tone && <span className="rounded-full bg-panel2 px-2.5 py-1 text-[11.5px] text-dim">tone: {scores.tone}</span>}
        {scores.rating != null && <span className="rounded-full bg-vi/10 px-2.5 py-1 text-[11.5px] text-vi">rating {pct(scores.rating)}</span>}
      </div>
      {scores.notes && <p className="mt-3 text-[12.5px] leading-relaxed text-dim">{scores.notes}</p>}
    </div>
  );
}

export function Transcript({ turns }: { turns: any[] }) {
  if (!turns?.length) return <p className="text-[12.5px] text-faint">No transcript.</p>;
  return (
    <div className="space-y-2.5">
      {turns.map((t, i) => {
        const agent = t.role === "agent";
        return (
          <div key={i} className={`flex ${agent ? "justify-start" : "justify-end"}`}>
            <div className={`max-w-[78%] rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed ${agent ? "border border-vi/25 bg-vi/5 text-ink" : "border border-line bg-panel2 text-dim"}`}>
              <div className={`mb-0.5 text-[10.5px] uppercase tracking-wider ${agent ? "text-vi" : "text-faint"}`}>{agent ? "Agent" : "Caller"}</div>
              {t.text}
            </div>
          </div>
        );
      })}
    </div>
  );
}
