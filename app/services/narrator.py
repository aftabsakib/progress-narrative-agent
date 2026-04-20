import anthropic
from datetime import date, timedelta
from app.config import settings
from app.services.master_context import MASTER_CONTEXT
from app.services.velocity import get_velocity_summary
from app.services.memory import get_parallels_for_stalled_contacts
from app.database import db

anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _get_day_comparison() -> str:
    today = date.today()
    yesterday = today - timedelta(days=1)

    today_count = db.table("activities")\
        .select("id")\
        .eq("date", today.isoformat())\
        .execute()

    yesterday_count = db.table("activities")\
        .select("id")\
        .eq("date", yesterday.isoformat())\
        .execute()

    tc = len(today_count.data)
    yc = len(yesterday_count.data)

    if yc == 0:
        direction = "no activity yesterday"
    elif tc > yc:
        direction = f"up {tc - yc} vs yesterday"
    elif tc < yc:
        direction = f"down {yc - tc} vs yesterday"
    else:
        direction = "same as yesterday"

    return f"Today: {tc} activities. Yesterday: {yc}. Direction: {direction}."


def _get_strategic_reframings() -> str:
    today = date.today()
    recent = db.table("activities")\
        .select("description, created_at")\
        .gte("date", (today - timedelta(days=1)).isoformat())\
        .execute()

    reframings = [
        a["description"] for a in recent.data
        if any(word in a["description"].lower() for word in [
            "repositioned", "reframed", "corrected", "revised", "updated positioning",
            "new approach", "changed", "strategic", "framework"
        ])
    ]
    if not reframings:
        return "None."
    return "\n".join(f"- {r}" for r in reframings[:5])


def generate_daily_brief() -> str:
    velocity = get_velocity_summary()
    today = date.today()

    # Only meaningful action types — not follow-ups or check-ins
    all_activities = db.table("activities")\
        .select("*")\
        .gte("date", (today - timedelta(days=1)).isoformat())\
        .execute()

    moved_types = {"proposal_sent", "call", "response_received", "asset_created", "strategic_reframing"}
    activities = type("R", (), {"data": [a for a in all_activities.data if a.get("activity_type") in moved_types]})()

    # Pipeline stage changes in the last 7 days
    stage_changes = db.table("pipeline_events")\
        .select("*, contacts(name, company)")\
        .gte("date", (today - timedelta(days=7)).isoformat())\
        .order("date", desc=True)\
        .execute()

    # Contacts with a sent artifact awaiting response — these are in a waiting state
    pending_response = db.table("artifacts")\
        .select("*, contacts(name, company)")\
        .eq("response_received", False)\
        .not_.is_("sent_date", "null")\
        .execute()

    overdue = db.table("commitments")\
        .select("*, contacts(name, company)")\
        .eq("status", "open")\
        .lt("due_date", today.isoformat())\
        .execute()

    upcoming = db.table("commitments")\
        .select("*, contacts(name, company)")\
        .eq("status", "open")\
        .gte("due_date", today.isoformat())\
        .lte("due_date", (today + timedelta(days=7)).isoformat())\
        .execute()

    pipeline = db.table("contacts")\
        .select("name, company, tier, role_stage, last_touched, pipeline_track, days_stalled")\
        .neq("status", "cadaver")\
        .execute()

    week_comparison = _get_day_comparison()
    reframings = _get_strategic_reframings()

    # Separate US-side contacts
    us_contacts = [c for c in pipeline.data if c.get("pipeline_track") == "us_side"]
    tier1_contacts = [c for c in pipeline.data if c.get("tier") == "1"]
    stalled_tier1 = [c for c in tier1_contacts if (c.get("days_stalled") or 0) >= 5]

    historical_parallels = get_parallels_for_stalled_contacts(stalled_tier1)

    day_yesterday = (today - timedelta(days=1)).strftime("%A")
    day_two_ago = (today - timedelta(days=2)).strftime("%A")

    context = f"""
DATE: {today.isoformat()}
AAEP DAYS REMAINING: {velocity['aaep_days_remaining']}

US SIDE OUTREACH — completed days only (daily target: {velocity['us_side_target']}):
{day_yesterday}: {velocity['us_side_touches_yesterday']}
{day_two_ago}: {velocity['us_side_touches_two_days_ago']}
NOTE: Sunday outreach is intentionally zero — treat as a rest day, not a failure.

PIPELINE STAGE CHANGES (last 7 days):
{chr(10).join(f"- {e['contacts']['name'] if e.get('contacts') else 'Unknown'} — Stage {e['from_stage']} to {e['to_stage']} on {e['date']}" for e in stage_changes.data) or "None"}

MEANINGFUL ACTIVITIES (last 24h — proposals sent, calls, responses received, assets created):
{chr(10).join(f"- [{a.get('created_by', '?')}] {a['description']}" for a in activities.data) or "None"}

STRATEGIC REFRAMINGS (last 24h):
{reframings}

PENDING RESPONSE — proposal or artifact sent, no reply yet (do not flag as stalled or at risk):
{chr(10).join(f"- {p['contacts']['name'] if p.get('contacts') else 'Unknown'} — {p['type']} sent {p['sent_date']}" for p in pending_response.data) or "None"}

TIER 1 PIPELINE ({len(tier1_contacts)} contacts):
{chr(10).join(f"- {c['name']} ({c.get('company', '')}) — Stage {c.get('role_stage', 1)} — last touched: {c.get('last_touched', 'never')} — stalled {c.get('days_stalled') or 0}d" for c in tier1_contacts) or "None"}

US SIDE ({len(us_contacts)} contacts):
{chr(10).join(f"- {c['name']} ({c.get('company', '')}) — last touched: {c.get('last_touched', 'never')}" for c in us_contacts) or "None tracked yet"}

OVERDUE COMMITMENTS ({len(overdue.data)}):
{chr(10).join(f"- {c['description']} — promised by {c['promised_by']} — due {c.get('due_date', 'no date')}" for c in overdue.data) or "None"}

UPCOMING COMMITMENTS — due within 7 days ({len(upcoming.data)}):
{chr(10).join(f"- {c['description']} — promised by {c['promised_by']} — due {c.get('due_date', 'no date')}" for c in upcoming.data) or "None"}

HISTORICAL PARALLELS (past activities similar to current stalls):
{historical_parallels}
"""

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=MASTER_CONTEXT,
        messages=[{
            "role": "user",
            "content": f"""Generate the Tangier daily brief using this structure:

1. VELOCITY CHECK — U.S.-side outreach only. Do not mention today's numbers — the day has not started. Use only completed days from the data. Three to five sentences maximum. No repetition — each fact once.

Write it as a pace report, not a status update. The reader wants to know: are we faster or slower than the day before, and what are two or three concrete actions that would increase the speed today. Name the actions specifically — not "reach out more" but "send connection requests to think tank researchers before noon." If Sunday shows zero, note it is a rest day and move on. Do not turn it into a warning.

State the AAEP days remaining once, as the urgency clock behind everything.

2. WHAT MOVED — draw only from PIPELINE STAGE CHANGES, MEANINGFUL ACTIVITIES, and STRATEGIC REFRAMINGS. A follow-up email sent to a contact who hasn't replied is not movement. A response received is. A stage change is. A proposal sent for the first time is. A second or third follow-up is not. One sentence per item. If nothing genuinely moved, say so in one sentence and move on.

3. WHAT IS AT RISK — contacts not touched and not in PENDING RESPONSE. Anything in PENDING RESPONSE is waiting — do not flag it as stalled, do not surface it as a priority, do not mention it unless the wait has exceeded 7 days. A contact not touched at all is different from a contact where a proposal is out. Name the difference. Order by urgency and strategic weight.

4. TODAY'S PRIORITIES — the primary action first, then every other action that genuinely needs to happen today. No artificial limit. Each one sentence, direct and specific. Not "consider sending" — "send it." Not "confirm whether X happened" — "call X, the meeting isn't confirmed." Every priority names the action and the person or thing it applies to. Include all upcoming commitments due within 48 hours.

Keep it tight. No filler. No hedging. Name the action, name the target, move on.

DATA:
{context}"""
        }]
    )
    return response.content[0].text


def generate_acceleration_brief() -> str:
    """Afternoon brief: what to build, improve, or systematize after outreach is done."""
    from datetime import timedelta

    today = date.today()

    activities = db.table("activities")\
        .select("*")\
        .eq("date", today.isoformat())\
        .execute()

    reframings = [
        a["description"] for a in activities.data
        if a.get("activity_type") == "strategic_reframing"
    ]

    outreach_count = len([
        a for a in activities.data
        if a.get("activity_type") in ("outreach", "us_side_outreach", "relationship_touch")
    ])

    context = f"""
DATE: {today.isoformat()}
OUTREACH DONE TODAY: {outreach_count}
STRATEGIC REFRAMINGS TODAY: {len(reframings)}

REFRAMINGS:
{chr(10).join(f"- {r}" for r in reframings) or "None"}

ALL ACTIVITY TODAY ({len(activities.data)}):
{chr(10).join(f"- [{a.get('activity_type', 'update')}] {a['description']}" for a in activities.data) or "None"}
"""

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=MASTER_CONTEXT,
        messages=[{
            "role": "user",
            "content": f"""Generate the afternoon acceleration brief. This is not a repeat of the morning brief.

Focus on:
1. WHAT GOT DONE TODAY — two to three sentences on actual output, not just activity count
2. WHAT TO BUILD OR IMPROVE — one to two specific things that would increase tomorrow's speed or effectiveness (agent improvements, messaging refinements, process fixes)
3. WHAT TO SYSTEMATIZE — one thing done manually today that should be automated or templated

Keep it under 200 words. Practical, not philosophical.

DATA:
{context}"""
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
DAYS SINCE LAST TOUCH: {contact.data.get('days_stalled', 0)}
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
            "content": f"Generate a role journey report. Include: current stage, time in stage, what moved them here, next concrete action to advance them.\n\n{context}"
        }]
    )
    return response.content[0].text
