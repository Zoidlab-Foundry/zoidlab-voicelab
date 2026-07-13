async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, { ...init, credentials: "include", headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
  if (!r.ok) {
    let detail = `HTTP ${r.status}`;
    try { detail = (await r.json()).detail || detail; } catch {}
    const e = new Error(detail) as Error & { status?: number }; e.status = r.status; throw e;
  }
  return r.json();
}

export const api = {
  entitlements: () => req<any>("/api/auth/entitlements"),
  stats: () => req<any>("/api/stats"),
  meta: () => req<{ relay_available: boolean; billing_mode: string; voice_models: string[]; default_model: string; max_turns_cap: number; transport: any }>("/api/meta"),

  agents: () => req<{ agents: any[] }>("/api/agents").then((d) => d.agents),
  agent: (id: string) => req<any>(`/api/agents/${id}`),
  createAgent: (b: any) => req<any>("/api/agents", { method: "POST", body: JSON.stringify(b) }).then((d) => d.agent),
  deleteAgent: (id: string) => req<any>(`/api/agents/${id}`, { method: "DELETE" }),

  scenarios: () => req<{ scenarios: any[] }>("/api/scenarios").then((d) => d.scenarios),
  createScenario: (b: any) => req<any>("/api/scenarios", { method: "POST", body: JSON.stringify(b) }).then((d) => d.scenario),
  deleteScenario: (id: string) => req<any>(`/api/scenarios/${id}`, { method: "DELETE" }),

  simulate: (b: { agent_id: string; scenario_id: string; model?: string; max_turns?: number }) =>
    req<any>("/api/simulate", { method: "POST", body: JSON.stringify(b) }),
  runs: () => req<{ runs: any[] }>("/api/runs").then((d) => d.runs),
  getRun: (id: string) => req<any>(`/api/runs/${id}`),

  exportUrl: (aid: string) => `/api/agents/${aid}/export`,
};

export const usd = (n: number) => "$" + (n ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 5 });
export const ms = (n: number | null) => (n == null ? "—" : n >= 1000 ? (n / 1000).toFixed(2) + "s" : Math.round(n) + "ms");
export const num = (n: number) => (n ?? 0).toLocaleString();
export const pct = (n: number | null | undefined) => (n == null ? "—" : Math.round(n * 100) + "%");
