from datetime import date
from app.services.extractor import extract_from_text
from app.services.embedder import embed_text
from app.database import db
from app.models.schemas import LogActivityInput


async def log_activity(input: LogActivityInput) -> str:
    extracted = await extract_from_text(input.text)

    results = {"activities_logged": 0, "commitments_logged": 0, "contacts_mentioned": []}

    for activity_desc in extracted.get("activities", []):
        embedding = embed_text(activity_desc)
        db.table("activities").insert({
            "date": date.today().isoformat(),
            "source": input.source,
            "description": activity_desc,
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

    results["contacts_mentioned"] = extracted.get("contacts_mentioned", [])

    return (
        f"Logged {results['activities_logged']} activities, "
        f"{results['commitments_logged']} commitments. "
        f"Contacts mentioned: {', '.join(results['contacts_mentioned']) or 'none'}."
    )
