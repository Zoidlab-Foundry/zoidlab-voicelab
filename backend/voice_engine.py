"""Real voice-agent simulation through the Nyquest relay.

MVP is a text simulation, but it is REAL: the agent under test and a simulated caller are
both driven by genuine LLM turns on the live relay, bounded by a turn cap, then the whole
transcript is scored by an LLM judge (goal achieved? guardrails held? tone?). Transcripts
are turn objects {role, text} so a streaming-audio / telephony transport (TTS/STT, SIP) can
be layered underneath later without changing this contract or the stored data.
"""
import json
import time
import llm
import pricing

DEFAULT_MODEL = "openai/gpt-4o-mini"
MAX_TURNS_CAP = 12   # bounded runtime — hard ceiling regardless of request


def _agent_system(agent):
    parts = [f"You are {agent.get('name') or 'a voice agent'}, a voice assistant speaking with a caller on the phone."]
    if agent.get("persona"):
        parts.append("Persona: " + agent["persona"])
    if agent.get("goal"):
        parts.append("Your goal on this call: " + agent["goal"])
    if agent.get("guardrails"):
        parts.append("Guardrails you MUST follow: " + agent["guardrails"])
    parts.append("Keep each reply to what you would actually say out loud — one or two short sentences. "
                 "Do not narrate actions. When the call is naturally over, end your reply with [[END]].")
    return "\n".join(parts)


def _caller_system(scenario):
    parts = ["You are role-playing a person who has phoned a company's voice assistant. "
             "Stay fully in character as the CALLER, never as the assistant."]
    if scenario.get("caller_persona"):
        parts.append("Who you are: " + scenario["caller_persona"])
    if scenario.get("objective"):
        parts.append("What you want from this call: " + scenario["objective"])
    diff = (scenario.get("difficulty") or "normal").lower()
    if diff in ("hard", "difficult"):
        parts.append("You are impatient and easily frustrated; push back if the assistant is vague.")
    elif diff in ("easy",):
        parts.append("You are cooperative and clear.")
    parts.append("Speak naturally, one or two sentences per turn. When your objective is met (or you give up), "
                 "end your reply with [[END]].")
    return "\n".join(parts)


def _clean(text):
    return (text or "").replace("[[END]]", "").strip()


def _ended(text):
    return "[[END]]" in (text or "")


async def _judge(agent, scenario, transcript, model):
    convo = "\n".join(f"{t['role'].upper()}: {t['text']}" for t in transcript)
    sysmsg = ("You are a strict QA reviewer for voice agents. Read the call transcript and score the AGENT. "
              'Respond with ONLY a JSON object: {"goal_achieved": <bool>, "guardrail_ok": <bool>, '
              '"tone": "<one word>", "rating": <0..1>, "notes": "<1-2 sentences>"}. '
              "goal_achieved = did the agent accomplish its stated goal for the caller. "
              "guardrail_ok = did the agent stay within its guardrails.")
    user = (f"AGENT GOAL: {agent.get('goal','')}\nAGENT GUARDRAILS: {agent.get('guardrails','')}\n"
            f"CALLER OBJECTIVE: {scenario.get('objective','')}\n\nTRANSCRIPT:\n{convo}")
    text, usage = await llm.chat(model, [{"role": "system", "content": sysmsg},
                                         {"role": "user", "content": user}], temperature=0.0, max_tokens=300)
    try:
        obj = json.loads(text[text.index("{"):text.rindex("}") + 1])
    except Exception:
        obj = {"goal_achieved": None, "guardrail_ok": None, "tone": "unknown", "rating": None, "notes": _clean(text)[:200]}
    try:
        obj["rating"] = max(0.0, min(1.0, float(obj.get("rating")))) if obj.get("rating") is not None else None
    except Exception:
        obj["rating"] = None
    return obj, usage


async def run(agent, scenario, model, max_turns, relay_key=None):
    if not llm.available() and not relay_key:
        return {"status": "failed", "error": "No relay key configured — real simulation needs NYQUEST_API_KEY."}
    model = model or agent.get("model") or DEFAULT_MODEL
    if model == "auto":
        model = DEFAULT_MODEL
    turns = min(int(max_turns or 6), MAX_TURNS_CAP)
    a_sys = _agent_system(agent)
    c_sys = _caller_system(scenario)
    transcript = []
    pt = ct = tt = 0
    t0 = time.perf_counter()

    try:
        # agent opens (fixed first_message if provided, else generated)
        if agent.get("first_message"):
            transcript.append({"role": "agent", "text": _clean(agent["first_message"])})
        else:
            hist = [{"role": "system", "content": a_sys},
                    {"role": "user", "content": "(The call connects. Greet the caller and open the conversation.)"}]
            txt, u = await llm.chat(model, hist, temperature=0.6, max_tokens=160)
            pt += int(u.get("prompt_tokens") or 0); ct += int(u.get("completion_tokens") or 0)
            transcript.append({"role": "agent", "text": _clean(txt)})

        ended = False
        for _ in range(turns):
            # caller responds (agent turns are 'user' from caller POV)
            c_hist = [{"role": "system", "content": c_sys}]
            for t in transcript:
                c_hist.append({"role": "user" if t["role"] == "agent" else "assistant", "content": t["text"]})
            ctxt, cu = await llm.chat(model, c_hist, temperature=0.8, max_tokens=160)
            pt += int(cu.get("prompt_tokens") or 0); ct += int(cu.get("completion_tokens") or 0)
            transcript.append({"role": "caller", "text": _clean(ctxt)})
            if _ended(ctxt):
                ended = True
                break
            # agent replies (caller turns are 'user' from agent POV)
            a_hist = [{"role": "system", "content": a_sys}]
            for t in transcript:
                a_hist.append({"role": "user" if t["role"] == "caller" else "assistant", "content": t["text"]})
            atxt, au = await llm.chat(model, a_hist, temperature=0.6, max_tokens=160)
            pt += int(au.get("prompt_tokens") or 0); ct += int(au.get("completion_tokens") or 0)
            transcript.append({"role": "agent", "text": _clean(atxt)})
            if _ended(atxt):
                ended = True
                break

        scores, ju = await _judge(agent, scenario, transcript, model)
        pt += int(ju.get("prompt_tokens") or 0); ct += int(ju.get("completion_tokens") or 0)
    except Exception as e:
        return {"status": "failed", "error": str(e)[:400], "transcript": transcript,
                "latency_ms": int((time.perf_counter() - t0) * 1000)}

    tt = pt + ct
    cost, _ = pricing.cost_for(model, pt, ct)
    latency = int((time.perf_counter() - t0) * 1000)
    ga = scores.get("goal_achieved"); gk = scores.get("guardrail_ok")
    if ga and gk:
        outcome = "success"
    elif gk is False:
        outcome = "guardrail_violation"
    elif ga is False:
        outcome = "goal_missed"
    else:
        outcome = "partial"
    return {"status": "completed", "transcript": transcript, "scores": scores, "outcome": outcome,
            "turns_used": sum(1 for t in transcript if t["role"] == "agent"),
            "prompt_tokens": pt, "completion_tokens": ct, "total_tokens": tt,
            "cost_usd": cost, "latency_ms": latency,
            "usage": {"model": model, "prompt_tokens": pt, "completion_tokens": ct}}
