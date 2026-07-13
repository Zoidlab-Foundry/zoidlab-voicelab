"""VoiceLab package export — a portable voice-agent definition, wrapped in the canonical
Foundry base envelope (blueprint §6.2 / Tier-3 Appendix C). Secrets are never included."""
import envelope


def to_package(agent, owner=None):
    payload = {
        "schema_version": "1.0",
        "package_type": "nyquest_voice_agent_package",
        "foundry_package": "voice",
        "resource_version": agent.get("version", "1.0.0"),
        "agent": {"name": agent.get("name"), "description": agent.get("description"),
                  "persona": agent.get("persona"), "goal": agent.get("goal"),
                  "guardrails": agent.get("guardrails"), "first_message": agent.get("first_message"),
                  "voice": agent.get("voice"), "model": agent.get("model")},
        "transport": {"mode": "text_simulation", "supports": ["streaming_audio", "telephony"], "implemented": ["text_simulation"]},
        "provider_config": {"model": agent.get("model")},
        "governance": {"human_review": True},
        "dependencies": [],
        "credential_refs": [],
    }
    return envelope.wrap("voice", "voice_agent", agent.get("id"), agent.get("version", "1.0.0"),
                         payload, nyquest_user_id=owner)
