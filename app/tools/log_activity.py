from datetime import date
from app.services.extractor import extract_from_text
from app.services.embedder import embed_text
from app.database import db
from app.models.schemas import LogActivityInput


def _resolve_contact_id(contact_name: str) -> str | None:
    if not contact_name:
        return None
    name = contact_name.strip()
    result = db.table("contacts").select("id").or_(
        f"name.ilike.{name},company.ilike.{name}"
    ).limit(1).execute()
    if result.data:
        return result.data[0]["id"]
    new_contact = db.table("contacts").insert({
        "name": name,
        "company": name,
        "tier": "3",
        "status": "active",
        "pipeline_track": "global_south",
        "notes": "Auto-created from activity log"
    }).execute()
    return new_contact.data[0]["id"] if new_contact.data else None


async def log_activity(input: LogActivityInput) -> str:
    extracted = await extract_from_text(input.text)

    results = {
        "activities_logged": 0,
        "commitments_logged": 0,
        "reframings_logged": 0,
        "contacts_mentioned": []
    }

    for activity in extracted.get("activities", []):
        if isinstance(activity, dict):
            description = activity.get("description", "")
            action_type = activity.get("action_type", "update")
            contact_name = activity.get("contact_name")
        else:
            description = str(activity)
            action_type = "update"
            contact_name = None

        if not description:
            continue

        contact_id = _resolve_contact_id(contact_name)
        embedding = embed_text(description)
        activity_date = input.activity_date or date.today()
        db.table("activities").insert({
            "date": activity_date.isoformat(),
            "source": input.source,
            "description": description,
            "activity_type": action_type,
            "contact_id": contact_id,
            "embedding": embedding,
            "created_by": input.created_by,
            "strategic_score": 0
        }).execute()
        results["activities_logged"] += 1

    for commitment in extracted.get("commitments", []):
        db.table("commitments").insert({
            "description": commitment["description"],
            "due_date": commitment.get("due_date"),
            "promised_by": commitment.get("promised_by", "unknown"),
            "status": "open"
        }).execute()
        results["commitments_logged"] += 1

    for trigger in extracted.get("intelligence_triggers", []):
        db.table("intelligence_triggers").insert({
            "type": trigger.get("type", "general"),
            "description": trigger.get("description", ""),
            "actioned": False
        }).execute()

    # Log strategic reframings as a special activity type
    for reframing in extracted.get("strategic_reframings", []):
        if reframing:
            embedding = embed_text(reframing)
            db.table("activities").insert({
                "date": date.today().isoformat(),
                "source": input.source,
                "description": reframing,
                "activity_type": "strategic_reframing",
                "embedding": embedding,
                "created_by": input.created_by,
                "strategic_score": 3
            }).execute()
            results["reframings_logged"] += 1

    results["contacts_mentioned"] = extracted.get("contacts_mentioned", [])

    # Auto-close commitments that match logged activities
    activity_descriptions = [
        a.get("description", "") if isinstance(a, dict) else str(a)
        for a in extracted.get("activities", [])
        if (a.get("description", "") if isinstance(a, dict) else str(a))
    ]
    from app.services.commitment_matcher import auto_close_matched_commitments
    closed = auto_close_matched_commitments(activity_descriptions)

    summary = (
        f"Logged {results['activities_logged']} activities, "
        f"{results['commitments_logged']} commitments"
    )
    if results["reframings_logged"]:
        summary += f", {results['reframings_logged']} strategic reframings"
    if results["contacts_mentioned"]:
        summary += f". Contacts: {', '.join(results['contacts_mentioned'])}"
    if closed:
        summary += f". {len(closed)} commitment(s) marked done automatically."

    return summary + "."
