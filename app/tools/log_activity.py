from datetime import date
from app.services.extractor import extract_from_text
from app.services.embedder import embed_text
from app.database import db
from app.models.schemas import LogActivityInput


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
        else:
            description = str(activity)
            action_type = "update"

        if not description:
            continue

        embedding = embed_text(description)
        db.table("activities").insert({
            "date": date.today().isoformat(),
            "source": input.source,
            "description": description,
            "activity_type": action_type,
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

    summary = (
        f"Logged {results['activities_logged']} activities, "
        f"{results['commitments_logged']} commitments"
    )
    if results["reframings_logged"]:
        summary += f", {results['reframings_logged']} strategic reframings"
    if results["contacts_mentioned"]:
        summary += f". Contacts: {', '.join(results['contacts_mentioned'])}"

    return summary + "."
