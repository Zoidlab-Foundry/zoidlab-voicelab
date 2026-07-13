"""Postgres data layer for VoiceLab with per-tenant Row-Level Security (§3.2).

Tenant isolation is enforced by the database: every tenant table carries owner_user_id, has
FORCE ROW LEVEL SECURITY, and a policy exposing only rows whose owner matches app.current_owner
(set per transaction) or is NULL (shared seed). App connections use the RLS-enforced role;
DDL + cross-tenant admin use the superuser. Public API mirrors the former sqlite database.py.
"""
import os
import uuid
import datetime

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json
from psycopg_pool import ConnectionPool

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://app_rls@127.0.0.1:5433/voicelab")
DATABASE_URL_ADMIN = os.environ.get("DATABASE_URL_ADMIN", "postgresql://foundry@127.0.0.1:5433/voicelab")
_pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=10, open=True, kwargs={"autocommit": False})


def admin_conn():
    return psycopg.connect(DATABASE_URL_ADMIN, row_factory=dict_row)


def now_iso():
    return datetime.datetime.utcnow().isoformat() + "Z"


def new_id(p):
    return f"{p}_{uuid.uuid4().hex[:12]}"


def _slug(s):
    import re
    return (re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:50] or "item") + "-" + uuid.uuid4().hex[:5]


class _tx:
    def __init__(self, owner):
        self.owner = owner or ""

    def __enter__(self):
        self.conn = _pool.getconn()
        self.cur = self.conn.cursor(row_factory=dict_row)
        self.cur.execute("SELECT set_config('app.current_owner', %s, true)", (self.owner,))
        return self.cur

    def __exit__(self, exc_type, exc, tb):
        try:
            self.conn.rollback() if exc_type else self.conn.commit()
        finally:
            self.cur.close()
            _pool.putconn(self.conn)


_TENANT_TABLES = ["voice_agents", "voice_scenarios", "voice_runs", "jobs"]


def init():
    with admin_conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT, name TEXT, created_at TEXT, updated_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS voice_agents (
            id TEXT PRIMARY KEY, owner_user_id TEXT, name TEXT NOT NULL, slug TEXT, description TEXT,
            persona TEXT, goal TEXT, guardrails TEXT, first_message TEXT, voice TEXT DEFAULT 'neutral',
            model TEXT DEFAULT 'auto', version TEXT DEFAULT '1.0.0', created_at TEXT, updated_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS voice_scenarios (
            id TEXT PRIMARY KEY, owner_user_id TEXT, name TEXT NOT NULL, slug TEXT, description TEXT,
            caller_persona TEXT, objective TEXT, difficulty TEXT DEFAULT 'normal', created_at TEXT, updated_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS voice_runs (
            id TEXT PRIMARY KEY, owner_user_id TEXT, agent_id TEXT, agent_name TEXT, scenario_id TEXT, scenario_name TEXT,
            model TEXT, status TEXT DEFAULT 'queued', max_turns INTEGER, turns_used INTEGER, transcript JSONB, scores JSONB,
            outcome TEXT, prompt_tokens INTEGER, completion_tokens INTEGER, total_tokens INTEGER, cost_usd DOUBLE PRECISION,
            latency_ms INTEGER, error TEXT, correlation_id TEXT, created_at TEXT, finished_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, owner_user_id TEXT, kind TEXT, resource_id TEXT, status TEXT, error TEXT,
            attempts INTEGER DEFAULT 0, celery_id TEXT, timeout_s INTEGER, created_at TEXT, started_at TEXT, finished_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS dead_letters (
            id TEXT PRIMARY KEY, owner_user_id TEXT, kind TEXT, resource_id TEXT, error TEXT, created_at TEXT)""")
        for t in _TENANT_TABLES:
            c.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
            c.execute(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY")
            c.execute(f"DROP POLICY IF EXISTS {t}_isolation ON {t}")
            c.execute(f"""CREATE POLICY {t}_isolation ON {t}
                USING (owner_user_id IS NULL OR owner_user_id = current_setting('app.current_owner', true))
                WITH CHECK (owner_user_id IS NULL OR owner_user_id = current_setting('app.current_owner', true))""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_vrun_owner ON voice_runs(owner_user_id, created_at)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_jobs_owner ON jobs(owner_user_id, created_at)")
        c.execute("GRANT USAGE ON SCHEMA public TO app_rls")
        c.execute("GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO app_rls")


def upsert_user(uid, email=None, name=None):
    if not uid:
        return
    now = now_iso()
    with _pool.connection() as c:
        c.execute("""INSERT INTO users (id,email,name,created_at,updated_at) VALUES (%s,%s,%s,%s,%s)
                     ON CONFLICT (id) DO UPDATE SET email=COALESCE(EXCLUDED.email,users.email),
                       name=COALESCE(EXCLUDED.name,users.name), updated_at=EXCLUDED.updated_at""",
                  (uid, email, name, now, now))


# --- agents ---
def list_agents(v=None):
    with _tx(v) as cur:
        cur.execute("SELECT * FROM voice_agents ORDER BY updated_at DESC")
        return cur.fetchall()


def get_agent(aid, v=None):
    with _tx(v) as cur:
        cur.execute("SELECT * FROM voice_agents WHERE id=%s", (aid,))
        return cur.fetchone()


def create_agent(d, owner):
    aid = new_id("agent"); now = now_iso()
    with _tx(owner) as cur:
        cur.execute("""INSERT INTO voice_agents (id,owner_user_id,name,slug,description,persona,goal,guardrails,
                       first_message,voice,model,version,created_at,updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'1.0.0',%s,%s)""",
                    (aid, owner, d["name"], _slug(d["name"]), d.get("description", ""), d.get("persona", ""),
                     d.get("goal", ""), d.get("guardrails", ""), d.get("first_message", ""),
                     d.get("voice", "neutral"), d.get("model", "auto"), now, now))
    return get_agent(aid, owner)


def delete_agent(aid, owner):
    a = get_agent(aid, owner)
    if not a or (a.get("owner_user_id") and a["owner_user_id"] != owner):
        return False
    with _tx(owner) as cur:
        cur.execute("DELETE FROM voice_agents WHERE id=%s", (aid,))
    return True


# --- scenarios ---
def list_scenarios(v=None):
    with _tx(v) as cur:
        cur.execute("SELECT * FROM voice_scenarios ORDER BY updated_at DESC")
        return cur.fetchall()


def get_scenario(sid, v=None):
    with _tx(v) as cur:
        cur.execute("SELECT * FROM voice_scenarios WHERE id=%s", (sid,))
        return cur.fetchone()


def create_scenario(d, owner):
    sid = new_id("scn"); now = now_iso()
    with _tx(owner) as cur:
        cur.execute("""INSERT INTO voice_scenarios (id,owner_user_id,name,slug,description,caller_persona,objective,difficulty,created_at,updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (sid, owner, d["name"], _slug(d["name"]), d.get("description", ""), d.get("caller_persona", ""),
                     d.get("objective", ""), d.get("difficulty", "normal"), now, now))
    return get_scenario(sid, owner)


def delete_scenario(sid, owner):
    s = get_scenario(sid, owner)
    if not s or (s.get("owner_user_id") and s["owner_user_id"] != owner):
        return False
    with _tx(owner) as cur:
        cur.execute("DELETE FROM voice_scenarios WHERE id=%s", (sid,))
    return True


# --- runs ---
def create_run(agent, scenario, model, max_turns, owner, correlation_id):
    rid = new_id("vsim")
    with _tx(owner) as cur:
        cur.execute("""INSERT INTO voice_runs (id,owner_user_id,agent_id,agent_name,scenario_id,scenario_name,
                       model,status,max_turns,correlation_id,created_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,'queued',%s,%s,%s)""",
                    (rid, owner, agent["id"], agent["name"], scenario["id"], scenario["name"],
                     model, max_turns, correlation_id, now_iso()))
    return rid


def finish_run(rid, res, owner=None):
    with _tx(owner) as cur:
        cur.execute("""UPDATE voice_runs SET status=%s, turns_used=%s, transcript=%s, scores=%s, outcome=%s,
                       prompt_tokens=%s, completion_tokens=%s, total_tokens=%s, cost_usd=%s, latency_ms=%s, error=%s, finished_at=%s
                       WHERE id=%s""",
                    (res.get("status", "failed"), res.get("turns_used"), Json(res.get("transcript", [])),
                     Json(res.get("scores")), res.get("outcome"), res.get("prompt_tokens"), res.get("completion_tokens"),
                     res.get("total_tokens"), res.get("cost_usd"), res.get("latency_ms"), res.get("error"), now_iso(), rid))


def set_run_status(rid, status, owner=None):
    with _tx(owner) as cur:
        cur.execute("UPDATE voice_runs SET status=%s WHERE id=%s", (status, rid))


def list_runs(v=None, limit=100):
    with _tx(v) as cur:
        cur.execute("""SELECT id,owner_user_id,agent_id,agent_name,scenario_id,scenario_name,model,status,outcome,
                       turns_used,total_tokens,cost_usd,latency_ms,scores,created_at FROM voice_runs
                       ORDER BY created_at DESC LIMIT %s""", (limit,))
        return cur.fetchall()


def get_run(rid, v=None):
    with _tx(v) as cur:
        cur.execute("SELECT * FROM voice_runs WHERE id=%s", (rid,))
        return cur.fetchone()


def stats(v=None):
    with _tx(v) as cur:
        cur.execute("SELECT COUNT(*) n FROM voice_agents"); agents = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) n FROM voice_scenarios"); scns = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) n FROM voice_runs"); runs = cur.fetchone()["n"]
        cur.execute("""SELECT COALESCE(SUM(cost_usd),0) cost, COALESCE(SUM(CASE WHEN outcome='success' THEN 1 ELSE 0 END),0) wins,
                       COALESCE(SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END),0) failed FROM voice_runs""")
        row = cur.fetchone()
    return {"agents": agents, "scenarios": scns, "runs": runs,
            "spend_usd": round(row["cost"] or 0, 4), "successes": row["wins"] or 0, "failed_runs": row["failed"] or 0}
