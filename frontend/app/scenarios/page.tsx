"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "../../lib/api";

const DIFF = ["easy", "normal", "hard"];

export default function ScenariosPage() {
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [f, setF] = useState<any>({ name: "", caller_persona: "", objective: "", difficulty: "normal" });

  const load = () => { api.scenarios().then(setScenarios).catch(() => {}); };
  useEffect(() => { load(); }, []);
  const set = (k: string, v: string) => setF((p: any) => ({ ...p, [k]: v }));

  async function save() {
    if (!f.name.trim()) return;
    setSaving(true);
    try { await api.createScenario(f); setOpen(false); setF({ name: "", caller_persona: "", objective: "", difficulty: "normal" }); load(); }
    finally { setSaving(false); }
  }
  async function del(id: string) { await api.deleteScenario(id).catch(() => {}); load(); }

  return (
    <div className="py-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-semibold">Scenarios</h1>
          <p className="mt-1 text-[13px] text-dim">A scenario is the caller the agent will face — who they are, what they want, and how hard they’ll be.</p>
        </div>
        <button onClick={() => setOpen(true)} className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-black hover:opacity-90">New scenario</button>
      </div>

      <div className="mt-6 grid gap-3 md:grid-cols-2">
        {scenarios.map((s) => (
          <div key={s.id} className="rounded-2xl border border-line bg-panel p-4">
            <div className="flex items-start justify-between gap-2">
              <div className="text-[14px] font-semibold text-ink">{s.name}</div>
              <span className={`rounded-full px-2 py-0.5 text-[10.5px] ${s.difficulty === "hard" ? "bg-bad/10 text-bad" : s.difficulty === "easy" ? "bg-ok/10 text-ok" : "bg-warn/10 text-warn"}`}>{s.difficulty}</span>
            </div>
            {s.caller_persona && <p className="mt-2 text-[12.5px] text-dim"><span className="text-faint">Caller:</span> {s.caller_persona}</p>}
            {s.objective && <p className="mt-1 text-[12px] text-dim"><span className="text-faint">Wants:</span> {s.objective}</p>}
            <div className="mt-3 flex items-center gap-3 text-[12px]">
              <Link href={`/simulate?scenario=${s.id}`} className="font-medium text-cy hover:underline">Use in simulation →</Link>
              <button onClick={() => del(s.id)} className="ml-auto text-faint hover:text-bad">delete</button>
            </div>
          </div>
        ))}
        {!scenarios.length && <div className="md:col-span-2 rounded-2xl border border-line bg-panel p-8 text-center text-[13px] text-faint">No scenarios yet.</div>}
      </div>

      {open && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/60 p-4 backdrop-blur-sm">
          <div className="mt-10 w-full max-w-xl rounded-2xl border border-line bg-panel p-6">
            <div className="flex items-center justify-between">
              <h2 className="text-[16px] font-semibold">New scenario</h2>
              <button onClick={() => setOpen(false)} className="text-faint hover:text-ink">✕</button>
            </div>
            <div className="mt-4 grid gap-3">
              <label className="block"><span className="text-[12px] text-dim">Name</span>
                <input value={f.name} onChange={(e) => set("name", e.target.value)} placeholder="e.g. Frustrated outage" className={inp} /></label>
              <label className="block"><span className="text-[12px] text-dim">Caller persona</span>
                <textarea value={f.caller_persona} onChange={(e) => set("caller_persona", e.target.value)} rows={2} placeholder="Who is calling and their state of mind." className={inp} /></label>
              <label className="block"><span className="text-[12px] text-dim">Objective</span>
                <textarea value={f.objective} onChange={(e) => set("objective", e.target.value)} rows={2} placeholder="What the caller is trying to achieve." className={inp} /></label>
              <label className="block"><span className="text-[12px] text-dim">Difficulty</span>
                <select value={f.difficulty} onChange={(e) => set("difficulty", e.target.value)} className={inp}>
                  {DIFF.map((d) => <option key={d} value={d}>{d}</option>)}
                </select></label>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button onClick={() => setOpen(false)} className="rounded-lg border border-line px-4 py-2 text-[13px] text-dim hover:text-ink">Cancel</button>
              <button onClick={save} disabled={saving || !f.name.trim()} className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-black hover:opacity-90 disabled:opacity-40">
                {saving ? "Saving…" : "Create scenario"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const inp = "mt-1 w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-[13px] text-ink outline-none focus:border-vi/50";
