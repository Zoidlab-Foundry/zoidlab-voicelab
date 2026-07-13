"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "../../lib/api";

const VOICES = ["neutral", "warm", "friendly", "professional", "energetic"];

export default function AgentsPage() {
  const [agents, setAgents] = useState<any[]>([]);
  const [meta, setMeta] = useState<any>(null);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [f, setF] = useState<any>({ name: "", description: "", persona: "", goal: "", guardrails: "", first_message: "", voice: "neutral", model: "auto" });

  const load = () => api.agents().then(setAgents).catch(() => {});
  useEffect(() => { load(); api.meta().then(setMeta).catch(() => {}); }, []);

  const set = (k: string, v: string) => setF((p: any) => ({ ...p, [k]: v }));

  async function save() {
    if (!f.name.trim()) return;
    setSaving(true);
    try {
      await api.createAgent(f);
      setOpen(false);
      setF({ name: "", description: "", persona: "", goal: "", guardrails: "", first_message: "", voice: "neutral", model: "auto" });
      load();
    } finally { setSaving(false); }
  }

  async function del(id: string) { await api.deleteAgent(id).catch(() => {}); load(); }

  return (
    <div className="py-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-semibold">Voice agents</h1>
          <p className="mt-1 text-[13px] text-dim">Each agent is a persona + a goal + the guardrails it must respect on a call. Design one, then test it in Simulate.</p>
        </div>
        <button onClick={() => setOpen(true)} className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-black hover:opacity-90">New agent</button>
      </div>

      <div className="mt-6 grid gap-3 md:grid-cols-2">
        {agents.map((a) => (
          <div key={a.id} className="rounded-2xl border border-line bg-panel p-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="text-[14px] font-semibold text-ink">{a.name}</div>
                <div className="mt-0.5 text-[11px] text-faint">voice: {a.voice} · {a.model}</div>
              </div>
              <span className="rounded-full bg-vi/10 px-2 py-0.5 text-[10.5px] text-vi">v{a.version}</span>
            </div>
            {a.goal && <p className="mt-2 text-[12.5px] text-dim"><span className="text-faint">Goal:</span> {a.goal}</p>}
            {a.guardrails && <p className="mt-1 line-clamp-2 text-[12px] text-dim"><span className="text-faint">Guardrails:</span> {a.guardrails}</p>}
            <div className="mt-3 flex items-center gap-3 text-[12px]">
              <Link href={`/simulate?agent=${a.id}`} className="font-medium text-cy hover:underline">Simulate →</Link>
              <a href={api.exportUrl(a.id)} target="_blank" className="text-dim hover:text-ink">Export package</a>
              <button onClick={() => del(a.id)} className="ml-auto text-faint hover:text-bad">delete</button>
            </div>
          </div>
        ))}
        {!agents.length && <div className="md:col-span-2 rounded-2xl border border-line bg-panel p-8 text-center text-[13px] text-faint">No agents yet.</div>}
      </div>

      {open && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/60 p-4 backdrop-blur-sm">
          <div className="mt-10 w-full max-w-2xl rounded-2xl border border-line bg-panel p-6">
            <div className="flex items-center justify-between">
              <h2 className="text-[16px] font-semibold">New voice agent</h2>
              <button onClick={() => setOpen(false)} className="text-faint hover:text-ink">✕</button>
            </div>
            <div className="mt-4 grid gap-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Name"><input value={f.name} onChange={(e) => set("name", e.target.value)} placeholder="e.g. Reservations Host" className={inp} /></Field>
                <Field label="Voice">
                  <select value={f.voice} onChange={(e) => set("voice", e.target.value)} className={inp}>
                    {VOICES.map((v) => <option key={v} value={v}>{v}</option>)}
                  </select>
                </Field>
              </div>
              <Field label="Persona"><textarea value={f.persona} onChange={(e) => set("persona", e.target.value)} rows={2} placeholder="Who the agent is and how it sounds." className={inp} /></Field>
              <Field label="Goal"><textarea value={f.goal} onChange={(e) => set("goal", e.target.value)} rows={2} placeholder="What the agent should accomplish on the call." className={inp} /></Field>
              <Field label="Guardrails"><textarea value={f.guardrails} onChange={(e) => set("guardrails", e.target.value)} rows={2} placeholder="Hard limits the agent must never cross." className={inp} /></Field>
              <Field label="First message (optional)"><input value={f.first_message} onChange={(e) => set("first_message", e.target.value)} placeholder="Leave blank to let the agent generate its greeting." className={inp} /></Field>
              <Field label="Model">
                <select value={f.model} onChange={(e) => set("model", e.target.value)} className={inp}>
                  <option value="auto">Auto ({meta?.default_model || "default"})</option>
                  {(meta?.voice_models || []).map((m: string) => <option key={m} value={m}>{m}</option>)}
                </select>
              </Field>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button onClick={() => setOpen(false)} className="rounded-lg border border-line px-4 py-2 text-[13px] text-dim hover:text-ink">Cancel</button>
              <button onClick={save} disabled={saving || !f.name.trim()} className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-black hover:opacity-90 disabled:opacity-40">
                {saving ? "Saving…" : "Create agent"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const inp = "mt-1 w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-[13px] text-ink outline-none focus:border-vi/50";
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="text-[12px] text-dim">{label}</span>{children}</label>;
}
