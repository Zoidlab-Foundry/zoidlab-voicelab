"""Seed VoiceLab with demo voice agents + caller scenarios (real definitions only).
No runs are seeded — simulations come only from real relay conversations the user triggers."""
import db_pg as db

_AGENTS = [
    {"name": "Reservations Host", "description": "Restaurant booking voice agent.",
     "persona": "A warm, efficient host at a busy Italian restaurant.",
     "goal": "Book, change, or cancel a table reservation and confirm the details back to the caller.",
     "guardrails": "Never take payment card numbers over the phone. Do not promise seating you can't confirm. "
                   "Escalate to a human for parties over 12.",
     "first_message": "Thanks for calling Evo Italian, this is the reservations line — how can I help you today?",
     "voice": "warm", "model": "auto"},
    {"name": "Support Triage", "description": "Tier-1 tech support voice agent.",
     "persona": "A calm, methodical support agent for a home-internet provider.",
     "goal": "Diagnose the caller's connectivity issue and either resolve it or open a ticket with the right details.",
     "guardrails": "Never ask for the account password. Don't blame the customer. Offer a callback if wait would exceed 5 minutes.",
     "first_message": "", "voice": "neutral", "model": "auto"},
    {"name": "Appointment Reminder", "description": "Outbound clinic reminder agent.",
     "persona": "A polite clinic assistant confirming an upcoming appointment.",
     "goal": "Confirm the appointment, or reschedule it if the caller can't make it.",
     "guardrails": "Do not disclose medical details. Verify identity by name and date of birth before discussing specifics.",
     "first_message": "", "voice": "friendly", "model": "auto"},
]

_SCENARIOS = [
    {"name": "Standard booking", "caller_persona": "A regular customer named Dana who wants a table for four on Friday at 7pm.",
     "objective": "Get a table for 4 booked for Friday 7pm under the name Dana.", "difficulty": "easy"},
    {"name": "Frustrated outage", "caller_persona": "Sam, whose internet has been down for two hours and has a work call soon.",
     "objective": "Get the internet working again or a firm ETA and a ticket number.", "difficulty": "hard"},
    {"name": "Reschedule request", "caller_persona": "Alex, who needs to move Tuesday's appointment to the following week.",
     "objective": "Reschedule the appointment to next week and get a confirmation.", "difficulty": "normal"},
]


def run():
    if db.list_agents(None) or db.list_scenarios(None):
        return 0
    for a in _AGENTS:
        db.create_agent(a, owner=None)
    for s in _SCENARIOS:
        db.create_scenario(s, owner=None)
    return len(_AGENTS) + len(_SCENARIOS)
