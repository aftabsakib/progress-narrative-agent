import anthropic
from datetime import date, timedelta
from app.config import settings
from app.services.master_context import MASTER_CONTEXT
from app.services.velocity import get_velocity_summary
from app.services.memory import get_parallels_for_stalled_contacts
from app.database import db

anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _get_week_comparison() -> str:
    today = date.today()
    last_week_start = (today - timedelta(days=7)).isoformat()

    this_week = db.table("activities")\
        .select("id")\
        .gte("date", (today - timedelta(days=7)).isoformat())\
        .execute()

    last_week = db.table("activities")\
        .select("id")\
        .gte("date", (today - timedelta(days=14)).isoformat())\
        .lt("date", last_week_start)\
        .execute()

    this_count = len(this_week.data)
    last_count = len(last_week.data)

    if last_count == 0:
        direction = "no prior week data"
    elif this_count > last_count:
        pct = round(((this_count - last_count) / last_count) * 100)
        direction = f"up {pct}% vs last week"
    elif this_count < last_count:
        pct = round(((last_count - this_count) / last_count) * 100)
        direction = f"down {pct}% vs last week"
    else:
        direction = "same as last week"

    return f"This week: {this_count} activities. Last week: {last_count}. Direction: {direction}."


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

    activities = db.table("activities")\
        .select("*")\
        .gte("date", (today - timedelta(days=1)).isoformat())\
        .execute()

    overdue = db.table("commitments")\
        .select("*, contacts(name, company)")\
        .eq("status", "open")\
        .lt("due_date", today.isoformat())\
        .execute()

    alerts = db.table("alerts")\
        .select("*")\
        .eq("actioned", False)\
        .order("created_at", desc=True)\
        .limit(10)\
        .execute()

    pipeline = db.table("contacts")\
        .select("name, company, tier, role_stage, last_touched, pipeline_track, days_stalled")\
        .neq("status", "cadaver")\
        .execute()

    week_comparison = _get_week_comparison()
    reframings = _get_strategic_reframings()

    # Separate US-side contacts
    us_contacts = [c for c in pipeline.data if c.get("pipeline_track") == "us_side"]
    tier1_contacts = [c for c in pipeline.data if c.get("tier") == "1"]
    stalled_tier1 = [c for c in tier1_contacts if (c.get("days_stalled") or 0) >= 5]

    historical_parallels = get_parallels_for_stalled_contacts(stalled_tier1)

    context = f"""
DATE: {today.isoformat()}
AAEP DAYS REMAINING: {velocity['aaep_days_remaining']}
OUTREACH TODAY: {velocity['outreach_count_today']}/{velocity['target']}
US SIDE TOUCHES TODAY: {velocity['us_side_touches_today']}
INMAILS REMAINING: {velocity['inmails_remaining']}

VELOCITY TREND:
{week_comparison}

STRATEGIC REFRAMINGS (last 24h):
{reframings}

ACTIVITIES TODAY ({len(activities.data)}):
{chr(10).join(f"- [{a.get('created_by', '?')}] {a['description']}" for a in activities.data) or "None logged"}

TIER 1 PIPELINE ({len(tier1_contacts)} contacts):
{chr(10).join(f"- {c['name']} ({c.get('company', '')}) — Stage {c.get('role_stage', 1)} — last touched: {c.get('last_touched', 'never')} — stalled {c.get('days_stalled') or 0}d" for c in tier1_contacts) or "None"}

US SIDE ({len(us_contacts)} contacts):
{chr(10).join(f"- {c['name']} ({c.get('company', '')}) — last touched: {c.get('last_touched', 'never')}" for c in us_contacts) or "None tracked yet"}

OVERDUE COMMITMENTS ({len(overdue.data)}):
{chr(10).join(f"- {c['description']} — promised by {c['promised_by']} — due {c.get('due_date', 'no date')}" for c in overdue.data) or "None"}

OPEN ALERTS ({len(alerts.data)}):
{chr(10).join(f"- [{a['severity'].upper()}] {a['message']}" for a in alerts.data) or "None"}

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

1. VELOCITY CHECK — outreach count vs target, week-on-week direction, U.S.-side status. Two to four sentences. Sober, not punitive.

2. WHAT MOVED — only things that actually advanced. Strategic reframings count. One to two sentences per item. One sentence for a win, move on.

3. WHAT IS AT RISK — items that are genuinely at risk, ordered by urgency and strategic weight. Name the specific problem and the specific action required. Distinguish between a proposal pending response (not stalled) and a contact not touched (stalled). US LinkedIn outreach is a named strategic lane — flag if zero. If HISTORICAL PARALLELS are provided, reference what worked in past similar situations — one sentence per stall, only if the parallel is genuinely instructive.

4. TODAY'S PRIORITIES — one primary action plus up to three supporting actions. Each one sentence. No more.

Keep it tight. Use plain English. Sound the alarm where warranted — not everywhere.

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
