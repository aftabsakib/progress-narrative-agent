import anthropic
from app.services.velocity import get_velocity_summary, calculate_days_stalled
from app.services.master_context import MASTER_CONTEXT
from app.config import settings
from app.database import db
from datetime import date, timedelta

anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


def get_velocity_report() -> str:
    v = get_velocity_summary()
    today = date.today()

    stalled_lines = []
    for contact in v["stalled_tier1"]:
        last = date.fromisoformat(contact["last_touched"]) if contact.get("last_touched") else None
        days = calculate_days_stalled(last)
        label = "not yet entered in the system" if days >= 999 else f"{days} days since last touch"
        stalled_lines.append(f"- {contact['name']} ({contact.get('company', '')}) — {label}")

    context = f"""
DATE: {today.isoformat()}
AAEP DAYS REMAINING: {v['aaep_days_remaining']}

OUTREACH — TODAY (day not yet complete):
Today so far: {v['outreach_count_today']} (target: {v['target']})

OUTREACH TREND — completed days only:
Yesterday: {v['outreach_count_yesterday']}
Day before yesterday: {v['us_side_touches_two_days_ago']}

U.S.-SIDE OUTREACH:
Today so far: {v['us_side_touches_today']} (target: {v['us_side_target']})
Yesterday (complete): {v['us_side_touches_yesterday']}
Two days ago (complete): {v['us_side_touches_two_days_ago']}

TIER 1 STATUS ({len(v['stalled_tier1'])} flagged):
{chr(10).join(stalled_lines) or "All Tier 1 contacts touched within five days."}
"""

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        system=MASTER_CONTEXT,
        messages=[{
            "role": "user",
            "content": f"""Write the velocity report. Cover three things only:

1. Today's outreach count vs the target of {v['target']}. Today is not yet complete — do not compare today to yesterday as if both days are done. Just state where today stands against the target.

2. U.S.-side outreach trend: compare yesterday vs two days ago (both complete days). State the direction plainly. Then state today's number so far.

3. Tier 1 contacts not yet entered in the system — list their names in one sentence. Do not say "999 days". Say they are not yet in the system.

IMPORTANT: Only use numbers from the DATA section below. Do not invent targets, quotas, or commitments that are not in the data.

Keep it under 120 words. No headers. No labels. Write the way Faisal writes.

DATA:
{context}"""
        }]
    )
    return response.content[0].text
