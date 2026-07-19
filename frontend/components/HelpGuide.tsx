"use client";
import { useEffect, useState } from "react";

/* In-app guide: what VoiceLab is and how to run your first simulated call.
   Auto-opens once per browser (localStorage) and lives behind the Guide nav button. */

const STORAGE_KEY = "vo_guide_v1";

const STEPS: { title: string; body: string }[] = [
  {
    title: "Design a voice agent",
    body: "On Agents, click New Agent and give it a persona, a goal, and the guardrails it must never cross on a call. Pick a voice style and a model (or leave it on Auto), and optionally set its opening line.",
  },
  {
    title: "Script the caller",
    body: "On Scenarios, define who will be on the other end of the line: the caller's persona, what they're trying to achieve, and how hard they'll push — easy, normal, or hard.",
  },
  {
    title: "Run the simulation",
    body: "On Simulate, pick an agent and a scenario, set the max turns, and launch. Both sides speak through the live Nyquest relay — real model calls in a durable background job, from queued to done.",
  },
  {
    title: "Read the transcript & verdict",
    body: "When the call ends, an LLM judge scores it: outcome (success, partial, guardrail violation), a rating, and per-dimension scores — alongside measured cost, latency, and tokens.",
  },
  {
    title: "Track every call in Runs",
    body: "Runs lists every simulated call you own with its outcome, judge rating, turns, cost, and latency. Open any run to replay the full transcript and token detail.",
  },
  {
    title: "Export the evidence",
    body: "Each agent card has an Export package link — a signed Foundry export of the agent definition and its run evidence, ready to drop in a ticket or hand to another Foundry app.",
  },
];

export default function HelpGuide() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    try {
      if (!localStorage.getItem(STORAGE_KEY)) setOpen(true);
    } catch {}
  }, []);

  const dismiss = () => {
    try { localStorage.setItem(STORAGE_KEY, "1"); } catch {}
    setOpen(false);
  };

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") dismiss(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="rounded-lg border border-line px-3 py-1.5 text-[12px] text-dim transition hover:text-ink hover:bg-white/5"
        aria-label="Open the VoiceLab guide"
      >
        Guide
      </button>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={dismiss} role="dialog" aria-modal="true" aria-label="VoiceLab guide">
          <div className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-xl border border-line bg-panel p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="mb-1 flex items-center gap-2">
              <span className="grid h-6 w-6 place-items-center rounded-md bg-vi/15 text-[13px] text-vi">◍</span>
              <h2 className="text-[16px] font-semibold">How VoiceLab works</h2>
            </div>
            <p className="mb-5 text-[13px] text-dim">
              Test voice agents against scripted callers — real simulated conversations, judged transcripts, and measured cost. Six steps from zero to evidence:
            </p>
            <ol className="space-y-4">
              {STEPS.map((s, i) => (
                <li key={i} className="flex gap-3">
                  <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-vi/15 text-[12px] font-semibold text-vi">{i + 1}</span>
                  <div>
                    <div className="text-[13.5px] font-medium">{s.title}</div>
                    <div className="text-[12.5px] leading-relaxed text-dim">{s.body}</div>
                  </div>
                </li>
              ))}
            </ol>
            <div className="mt-6 flex items-center justify-between border-t border-line pt-4">
              <a href="https://foundry.zoidlab.ai" className="text-[12px] text-dim hover:text-ink">◈ All Foundry apps</a>
              <button onClick={dismiss} className="rounded-lg bg-vi px-4 py-1.5 text-[12.5px] font-semibold text-black hover:opacity-90">
                Got it
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
