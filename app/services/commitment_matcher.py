import anthropic
import json
from app.config import settings
from app.database import db

anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


def auto_close_matched_commitments(activity_descriptions: list[str]) -> list[str]:
    """Check open commitments against logged activities. Close any that match."""
    if not activity_descriptions:
        return []

    open_commitments = db.table("commitments")\
        .select("id, description, promised_by")\
        .eq("status", "open")\
        .execute()

    if not open_commitments.data:
        return []

    commitments_text = "\n".join(
        f"- ID: {c['id']} | {c['description']} (promised by {c['promised_by']})"
        for c in open_commitments.data
    )
    activities_text = "\n".join(f"- {d}" for d in activity_descriptions)

    response = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"""You are matching logged activities to open commitments to determine which commitments are now done.

ACTIVITIES JUST LOGGED:
{activities_text}

OPEN COMMITMENTS:
{commitments_text}

Return a JSON array of commitment IDs that are clearly fulfilled by the activities above. Only include a commitment if the activity is a clear match — same contact, same action (e.g. "sent outreach to Nizar Bouguila" closes "Send Inwi outreach to Nizar Bouguila"). If uncertain, do not include it.

Return only a JSON array of UUID strings. Example: ["uuid1", "uuid2"]. If none match, return [].
"""
        }]
    )

    raw = response.content[0].text.strip()
    try:
        matched_ids = json.loads(raw)
    except json.JSONDecodeError:
        return []

    closed = []
    for commitment_id in matched_ids:
        db.table("commitments")\
            .update({"status": "done"})\
            .eq("id", commitment_id)\
            .execute()
        closed.append(commitment_id)

    return closed
