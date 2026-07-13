"""ZoidLab VoiceLab API — Foundry Package 11, AI Voice Lab.

Design voice agents (persona + goal + guardrails + first message), define caller scenarios,
and run REAL simulated conversations through the Nyquest relay (agent and caller are both
real LLM turns, bounded by a turn cap), then score the transcript with an LLM judge. Every
data endpoint requires Nyquest Pro (backend fail-closed). Simulations emit SpendGuard usage
and preflight through TrustGate. NOTE: uses /api (platform-consistent).
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

import database as db
import llm
import voice_engine
import exporter
import foundry
import jobs
import seed_voice
from auth import session, require_pro, relay_key, entitlement


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    jobs.init()
    interrupted = jobs.reconcile()
    if interrupted:
        print(f"[voicelab] reconciled {interrupted} interrupted job(s)")
    n = seed_voice.run()
    if n:
        print(f"[voicelab] seeded {n} demo agents + scenarios")
    yield


app = FastAPI(title="ZoidLab VoiceLab API", lifespan=lifespan)


def require_owner(request: Request):
    o = require_pro(request)
    s = session(request)
    db.upsert_user(o, s.get("email") if s else None, s.get("name") if s else None)
    return o


@app.get("/api/health")
def health():
    return {"ok": True, "service": "voicelab"}


@app.get("/api/auth/me")
def auth_me(request: Request):
    s = session(request)
    if not s:
        return {"authenticated": False}
    return {"authenticated": True, "user_id": s.get("sub"), "email": s.get("email"),
            "name": s.get("name"), "tier": s.get("tier")}


@app.get("/api/auth/entitlements")
def auth_entitlements(request: Request):
    return entitlement(request)


@app.get("/api/meta")
async def meta():
    try:
        models = await llm.featured_models()
    except Exception:
        models = ["auto"]
    return {"relay_available": llm.available(), "billing_mode": llm.billing_mode(),
            "voice_models": models, "default_model": voice_engine.DEFAULT_MODEL,
            "max_turns_cap": voice_engine.MAX_TURNS_CAP,
            "transport": {"implemented": ["text_simulation"], "planned": ["streaming_audio", "telephony"]}}


@app.get("/api/stats")
def stats(request: Request, owner: str = Depends(require_owner)):
    return db.stats(owner)


# --- agents ---
class AgentBody(BaseModel):
    name: str
    description: Optional[str] = ""
    persona: Optional[str] = ""
    goal: Optional[str] = ""
    guardrails: Optional[str] = ""
    first_message: Optional[str] = ""
    voice: Optional[str] = "neutral"
    model: Optional[str] = "auto"


@app.get("/api/agents")
def agents(request: Request, owner: str = Depends(require_owner)):
    return {"agents": db.list_agents(owner)}


@app.get("/api/agents/{aid}")
def get_agent(aid: str, request: Request, owner: str = Depends(require_owner)):
    a = db.get_agent(aid, owner)
    if not a:
        raise HTTPException(404, "not_found")
    return a


@app.post("/api/agents")
def create_agent(body: AgentBody, owner: str = Depends(require_owner)):
    return {"ok": True, "agent": db.create_agent(body.model_dump(), owner)}


@app.delete("/api/agents/{aid}")
def delete_agent(aid: str, owner: str = Depends(require_owner)):
    if not db.delete_agent(aid, owner):
        raise HTTPException(404, "not_found_or_forbidden")
    return {"ok": True}


# --- scenarios ---
class ScenarioBody(BaseModel):
    name: str
    description: Optional[str] = ""
    caller_persona: Optional[str] = ""
    objective: Optional[str] = ""
    difficulty: Optional[str] = "normal"


@app.get("/api/scenarios")
def scenarios(request: Request, owner: str = Depends(require_owner)):
    return {"scenarios": db.list_scenarios(owner)}


@app.post("/api/scenarios")
def create_scenario(body: ScenarioBody, owner: str = Depends(require_owner)):
    return {"ok": True, "scenario": db.create_scenario(body.model_dump(), owner)}


@app.delete("/api/scenarios/{sid}")
def delete_scenario(sid: str, owner: str = Depends(require_owner)):
    if not db.delete_scenario(sid, owner):
        raise HTTPException(404, "not_found_or_forbidden")
    return {"ok": True}


# --- simulate ---
class SimBody(BaseModel):
    agent_id: str
    scenario_id: str
    model: Optional[str] = None
    max_turns: Optional[int] = 6


@app.post("/api/simulate")
async def simulate(body: SimBody, request: Request, owner: str = Depends(require_owner)):
    agent = db.get_agent(body.agent_id, owner)
    scenario = db.get_scenario(body.scenario_id, owner)
    if not agent:
        raise HTTPException(404, "agent_not_found")
    if not scenario:
        raise HTTPException(404, "scenario_not_found")
    if not llm.available():
        raise HTTPException(503, "relay_unavailable: real simulation needs a relay key")
    model = body.model or agent.get("model") or voice_engine.DEFAULT_MODEL
    import uuid as _uuid
    corr = "corr_" + _uuid.uuid4().hex[:12]
    foundry.set_session(request.cookies.get("zb_session"))
    pf = await foundry.trustgate_preflight(
        {"prompt": (agent.get("goal") or "") + " / " + (scenario.get("objective") or ""),
         "model": model, "data_classification": "internal", "context_type": "voice_agent"},
        correlation_id=corr)
    if pf.get("decision") == "blocked":
        rid = db.create_run(agent, scenario, model, body.max_turns or 6, owner, corr)
        db.finish_run(rid, {"status": "blocked", "outcome": "blocked",
                            "error": "TrustGate blocked: " + "; ".join(pf.get("reasons") or [])})
        return db.get_run(rid, owner)
    rid = db.create_run(agent, scenario, model, body.max_turns or 6, owner, corr)
    rk = relay_key(request)
    llm.set_relay_auth(rk)

    async def runner():
        res = await voice_engine.run(agent, scenario, model, body.max_turns, relay_key=rk)
        try:
            await foundry.emit_spend(res.get("usage"), resource_id=rid, feature=agent.get("name"),
                                     correlation_id=corr, environment="development")
        except Exception:
            pass
        return res

    job = jobs.submit(owner, "voice_simulation", rid, runner,
                      on_result=lambda res: db.finish_run(rid, res), timeout_s=180)
    return {"job_id": job["id"], "run_id": rid, "status": job["status"], "run": db.get_run(rid, owner)}


# --- jobs ---
@app.get("/api/jobs/{jid}")
def get_job(jid: str, request: Request, owner: str = Depends(require_owner)):
    j = jobs.get(jid, owner)
    if not j:
        raise HTTPException(404, "not_found")
    return j


@app.get("/api/jobs")
def list_jobs(request: Request, owner: str = Depends(require_owner)):
    return {"jobs": jobs.list_jobs(owner)}


@app.post("/api/jobs/{jid}/cancel")
def cancel_job(jid: str, request: Request, owner: str = Depends(require_owner)):
    return {"ok": jobs.cancel(jid, owner)}


@app.get("/api/runs")
def runs(request: Request, owner: str = Depends(require_owner)):
    return {"runs": db.list_runs(owner)}


@app.get("/api/runs/{rid}")
def get_run(rid: str, request: Request, owner: str = Depends(require_owner)):
    r = db.get_run(rid, owner)
    if not r:
        raise HTTPException(404, "not_found")
    return r


# --- export ---
@app.get("/api/agents/{aid}/export")
def export_agent(aid: str, request: Request, owner: str = Depends(require_owner)):
    a = db.get_agent(aid, owner)
    if not a:
        raise HTTPException(404, "not_found")
    return exporter.to_package(a, owner=owner)
