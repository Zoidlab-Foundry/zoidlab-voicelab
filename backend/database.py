"""SQLite persistence for ZoidLab VoiceLab (Foundry Package 11 — AI Voice Lab).

MVP vertical slice: design voice agents (persona + goal + guardrails + first message),
define caller scenarios, and run REAL simulated conversations through the Nyquest relay
(the agent and a simulated caller are both driven by real LLM turns), then score the
transcript with an LLM judge. Transcripts are stored as turn objects {role, text, ...} so
a streaming-audio / telephony transport can be layered on later without a data redesign.
Owner = Nyquest user id; seed (owner NULL) is shared.
"""
import os
import json
import uuid
import sqlite3
import datetime

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "voicelab.db")


def now_iso():
    return datetime.datetime.utcnow().isoformat() + "Z"


def new_id(p):
    return f"{p}_{uuid.uuid4().hex[:12]}"


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _j(v):
    return json.dumps(v)


def _pj(v, d=None):
    try:
        return json.loads(v) if v is not None else d
    except Exception:
        return d


def _slug(s):
    import re
    return (re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:50] or "item") + "-" + uuid.uuid4().hex[:5]


def init():
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT, name TEXT, created_at TEXT, updated_at TEXT);
            CREATE TABLE IF NOT EXISTS voice_agents (
                id TEXT PRIMARY KEY, owner_user_id TEXT, name TEXT NOT NULL, slug TEXT, description TEXT,
                persona TEXT, goal TEXT, guardrails TEXT, first_message TEXT, voice TEXT DEFAULT 'neutral',
                model TEXT DEFAULT 'auto', version TEXT DEFAULT '1.0.0', created_at TEXT, updated_at TEXT);
            CREATE INDEX IF NOT EXISTS idx_agent_owner ON voice_agents(owner_user_id);
            CREATE TABLE IF NOT EXISTS voice_scenarios (
                id TEXT PRIMARY KEY, owner_user_id TEXT, name TEXT NOT NULL, slug TEXT, description TEXT,
                caller_persona TEXT, objective TEXT, difficulty TEXT DEFAULT 'normal', created_at TEXT, updated_at TEXT);
            CREATE INDEX IF NOT EXISTS idx_scn_owner ON voice_scenarios(owner_user_id);
            CREATE TABLE IF NOT EXISTS voice_runs (
                id TEXT PRIMARY KEY, owner_user_id TEXT, agent_id TEXT, agent_name TEXT,
                scenario_id TEXT, scenario_name TEXT, model TEXT, status TEXT DEFAULT 'queued',
                max_turns INTEGER, turns_used INTEGER, transcript TEXT, scores TEXT, outcome TEXT,
                prompt_tokens INTEGER, completion_tokens INTEGER, total_tokens INTEGER, cost_usd REAL,
                latency_ms INTEGER, error TEXT, correlation_id TEXT, created_at TEXT, finished_at TEXT);
            CREATE INDEX IF NOT EXISTS idx_run_owner ON voice_runs(owner_user_id, created_at);
            """
        )


def _vis(col="owner_user_id"):
    return f"({col} IS NULL OR {col}=?)"


def upsert_user(uid, email=None, name=None):
    if not uid:
        return
    now = now_iso()
    with _conn() as c:
        c.execute("""INSERT INTO users (id,email,name,created_at,updated_at) VALUES (?,?,?,?,?)
                     ON CONFLICT(id) DO UPDATE SET email=COALESCE(excluded.email,users.email),
                       name=COALESCE(excluded.name,users.name), updated_at=excluded.updated_at""",
                  (uid, email, name, now, now))


# --- agents ---
def _agent_out(r):
    return dict(r) if r else None


def list_agents(v=None):
    with _conn() as c:
        rows = c.execute(f"SELECT * FROM voice_agents WHERE {_vis()} ORDER BY updated_at DESC", (v,)).fetchall()
    return [_agent_out(r) for r in rows]


def get_agent(aid, v=None):
    with _conn() as c:
        r = c.execute(f"SELECT * FROM voice_agents WHERE id=? AND {_vis()}", (aid, v)).fetchone()
    return _agent_out(r)


def create_agent(d, owner):
    aid = new_id("agent"); now = now_iso()
    with _conn() as c:
        c.execute("""INSERT INTO voice_agents (id,owner_user_id,name,slug,description,persona,goal,guardrails,
                     first_message,voice,model,version,created_at,updated_at)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,'1.0.0',?,?)""",
                  (aid, owner, d["name"], _slug(d["name"]), d.get("description", ""), d.get("persona", ""),
                   d.get("goal", ""), d.get("guardrails", ""), d.get("first_message", ""),
                   d.get("voice", "neutral"), d.get("model", "auto"), now, now))
    return get_agent(aid, owner)


def delete_agent(aid, owner):
    a = get_agent(aid, owner)
    if not a or (a.get("owner_user_id") and a["owner_user_id"] != owner):
        return False
    with _conn() as c:
        c.execute("DELETE FROM voice_agents WHERE id=?", (aid,))
    return True


# --- scenarios ---
def list_scenarios(v=None):
    with _conn() as c:
        rows = c.execute(f"SELECT * FROM voice_scenarios WHERE {_vis()} ORDER BY updated_at DESC", (v,)).fetchall()
    return [dict(r) for r in rows]


def get_scenario(sid, v=None):
    with _conn() as c:
        r = c.execute(f"SELECT * FROM voice_scenarios WHERE id=? AND {_vis()}", (sid, v)).fetchone()
    return dict(r) if r else None


def create_scenario(d, owner):
    sid = new_id("scn"); now = now_iso()
    with _conn() as c:
        c.execute("""INSERT INTO voice_scenarios (id,owner_user_id,name,slug,description,caller_persona,objective,difficulty,created_at,updated_at)
                     VALUES (?,?,?,?,?,?,?,?,?,?)""",
                  (sid, owner, d["name"], _slug(d["name"]), d.get("description", ""), d.get("caller_persona", ""),
                   d.get("objective", ""), d.get("difficulty", "normal"), now, now))
    return get_scenario(sid, owner)


def delete_scenario(sid, owner):
    s = get_scenario(sid, owner)
    if not s or (s.get("owner_user_id") and s["owner_user_id"] != owner):
        return False
    with _conn() as c:
        c.execute("DELETE FROM voice_scenarios WHERE id=?", (sid,))
    return True


# --- runs (simulations) ---
def create_run(agent, scenario, model, max_turns, owner, correlation_id):
    rid = new_id("vsim")
    with _conn() as c:
        c.execute("""INSERT INTO voice_runs (id,owner_user_id,agent_id,agent_name,scenario_id,scenario_name,
                     model,status,max_turns,correlation_id,created_at)
                     VALUES (?,?,?,?,?,?,?,'running',?,?,?)""",
                  (rid, owner, agent["id"], agent["name"], scenario["id"], scenario["name"],
                   model, max_turns, correlation_id, now_iso()))
    return rid


def finish_run(rid, res):
    with _conn() as c:
        c.execute("""UPDATE voice_runs SET status=?, turns_used=?, transcript=?, scores=?, outcome=?,
                     prompt_tokens=?, completion_tokens=?, total_tokens=?, cost_usd=?, latency_ms=?, error=?, finished_at=?
                     WHERE id=?""",
                  (res.get("status", "failed"), res.get("turns_used"), _j(res.get("transcript", [])),
                   _j(res.get("scores")), res.get("outcome"),
                   res.get("prompt_tokens"), res.get("completion_tokens"), res.get("total_tokens"),
                   res.get("cost_usd"), res.get("latency_ms"), res.get("error"), now_iso(), rid))


def _run_out(r):
    if not r:
        return None
    d = dict(r)
    d["transcript"] = _pj(d.get("transcript"), []); d["scores"] = _pj(d.get("scores"), None)
    return d


def list_runs(v=None, limit=100):
    with _conn() as c:
        rows = c.execute(f"""SELECT id,owner_user_id,agent_id,agent_name,scenario_id,scenario_name,model,status,
                             outcome,turns_used,total_tokens,cost_usd,latency_ms,scores,created_at FROM voice_runs WHERE {_vis()}
                             ORDER BY created_at DESC LIMIT ?""", (v, limit)).fetchall()
    out = []
    for r in rows:
        d = dict(r); d["scores"] = _pj(d.get("scores"), None); out.append(d)
    return out


def get_run(rid, v=None):
    with _conn() as c:
        r = c.execute(f"SELECT * FROM voice_runs WHERE id=? AND {_vis()}", (rid, v)).fetchone()
    return _run_out(r)


def stats(v=None):
    with _conn() as c:
        agents = c.execute(f"SELECT COUNT(*) n FROM voice_agents WHERE {_vis()}", (v,)).fetchone()["n"]
        scns = c.execute(f"SELECT COUNT(*) n FROM voice_scenarios WHERE {_vis()}", (v,)).fetchone()["n"]
        runs = c.execute(f"SELECT COUNT(*) n FROM voice_runs WHERE {_vis()}", (v,)).fetchone()["n"]
        row = c.execute(f"""SELECT COALESCE(SUM(cost_usd),0) cost,
                            SUM(CASE WHEN outcome='success' THEN 1 ELSE 0 END) wins,
                            SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) failed FROM voice_runs WHERE {_vis()}""", (v,)).fetchone()
    return {"agents": agents, "scenarios": scns, "runs": runs,
            "spend_usd": round(row["cost"] or 0, 4), "successes": row["wins"] or 0,
            "failed_runs": row["failed"] or 0}
