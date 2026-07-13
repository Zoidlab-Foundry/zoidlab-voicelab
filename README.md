# ZoidLab VoiceLab — Foundry Package 11

AI Voice Lab. Design voice agents (persona + goal + guardrails + first message), define
caller scenarios, and run **real simulated conversations** through the Nyquest relay — the
agent under test and a simulated caller are both driven by genuine LLM turns, bounded by a
turn cap — then score the transcript with an LLM judge (goal achieved? guardrails held?).

MVP transport is text simulation; transcripts are stored as turn objects `{role, text}` so a
streaming-audio / telephony transport (TTS/STT, SIP) can be layered underneath later without
a data-model change. Every data endpoint requires Nyquest Pro (fail-closed on the Next
middleware AND the FastAPI backend). Simulations emit SpendGuard usage events and preflight
through TrustGate.

## Layout
- `backend/` — FastAPI + SQLite. `voice_engine.py` runs the two-persona relay conversation +
  LLM judge; `database.py` owner-scoped agents/scenarios/runs; `main.py` the `/api` surface.
- `frontend/` — Next 15 + React 19 (teal theme). Dashboard, Agents, Scenarios, Simulate, Runs.

## Run locally
Backend: `cd backend && python -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/uvicorn main:app --port 8705`
Frontend: `cd frontend && npm install && VOICELAB_API_URL=http://127.0.0.1:8705 npm run dev` (port 3705)

Live: https://voice.zoidlab.ai
