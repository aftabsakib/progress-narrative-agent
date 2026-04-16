import anthropic
from datetime import date
from app.config import settings
from app.services.master_context import MASTER_CONTEXT
from app.services.velocity import get_velocity_summary
from app.database import db

anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


def generate_daily_brief() -> str:
    velocity = get_velocity_summary()

    activities = db.table("activities")\
        .select("*")\
        .eq("date", date.today().isoformat())\
        .execute()

    overdue = db.table("commitments")\
        .select("*, contacts(name, company)")\
        .eq("status", "open")\
        .lt("due_date", date.today().isoformat())\
        .execute()

    alerts = db.table("alerts")\
        .select("*")\
        .eq("actioned", False)\
        .order("created_at", desc=True)\
        .limit(10)\
        .execute()

    context = f"""
DATE: {date.today().isoformat()}
AAEP DAYS REMAINING: {velocity['aaep_days_remaining']}
OUTREACH TODAY: {velocity['outreach_count_today']}/{velocity['target']}
TIER 1 STALLED: {len(velocity['stalled_tier1'])} entities
US SIDE TOUCHES TODAY: {velocity['us_side_touches_today']}
INMAILS REMAINING: {velocity['inmails_remaining']}

ACTIVITIES TODAY ({len(activities.data)}):
{chr(10).join(f"- {a['description']}" for a in activities.data) or "None logged"}

OVERDUE COMMITMENTS ({len(overdue.data)}):
{chr(10).join(f"- {c['description']} (promised by {c['promised_by']})" for c in overdue.data) or "None"}

OPEN ALERTS:
{chr(10).join(f"- [{a['severity'].upper()}] {a['message']}" for a in alerts.data) or "None"}
"""

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=MASTER_CONTEXT,
        messages=[{
            "role": "user",
            "content": f"Generate the daily brief for Tangier. Format: (1) Velocity Check, (2) What Moved, (3) What Is At Risk, (4) Today's Priority — one action only.\n\nDATA:\n{context}"
        }]
    )
    return response.content[0].text


def generate_role_journey_report(contact_id: str) -> str:
    contact = db.table("contacts").select("*").eq("id", contact_id).single().execute()
    events = db.table("pipeline_events")\
        .select("*")\
        .eq("contact_id", contact_id)\
        .order("date", desc=True)\
        .execute()
    artifacts = db.table("artifacts")\
        .select("*")\
        .eq("contact_id", contact_id)\
        .execute()

    stage_names = {
        1: "Role Identification",
        2: "Role Packet / Initial Mandate",
        3: "Role Preparation",
        4: "Role Buy-in / Commitment",
        5: "Role Execution",
        6: "New Role Creation"
    }

    context = f"""
CONTACT: {contact.data['name']}, {contact.data.get('title', '')}, {contact.data.get('company', '')}
TIER: {contact.data.get('tier')}
CURRENT STAGE: {contact.data.get('role_stage')} — {stage_names.get(contact.data.get('role_stage', 1), 'Unknown')}
DAYS STALLED: {contact.data.get('days_stalled', 0)}
STATUS: {contact.data.get('status')}

STAGE HISTORY:
{chr(10).join(f"- {e['date']}: Stage {e['from_stage']} -> {e['to_stage']}" for e in events.data) or "No stage movements recorded"}

ARTIFACTS SENT:
{chr(10).join(f"- {a['type']} sent {a.get('sent_date', 'unsent')} — response: {a['response_received']}" for a in artifacts.data) or "None"}
"""

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        system=MASTER_CONTEXT,
        messages=[{
            "role": "user",
            "content": f"Generate a role journey report for this principal. Include: current stage, time in stage, what moved them here, next concrete action to advance them.\n\n{context}"
        }]
    )
    return response.content[0].text
