from app.database import db


def get_recent_activity(hours: int = 24, limit: int = 30) -> str:
    from datetime import datetime, timezone, timedelta

    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    rows = db.table("activities")\
        .select("*")\
        .gte("created_at", since)\
        .order("created_at", desc=True)\
        .limit(limit)\
        .execute()

    if not rows.data:
        return f"No activities logged in the last {hours} hours."

    # Group by contact
    by_contact: dict = {}
    no_contact = []

    for r in rows.data:
        contact = r.get("contact_name") or r.get("contact_id") or None
        action_type = r.get("activity_type", "update")
        description = r.get("description", "")
        who = r.get("created_by", "?")
        ts = r.get("created_at", "")[:16].replace("T", " ")

        entry = f"    [{who}] {description} ({ts})"

        if contact:
            if contact not in by_contact:
                by_contact[contact] = []
            by_contact[contact].append(entry)
        else:
            no_contact.append(entry)

    lines = [f"ACTIVITY LOG — last {hours}h ({len(rows.data)} entries)", ""]

    if by_contact:
        lines.append("BY CONTACT:")
        for contact, entries in by_contact.items():
            lines.append(f"  {contact}:")
            lines.extend(entries)
            lines.append("")

    if no_contact:
        lines.append("OTHER ACTIVITY:")
        lines.extend(no_contact)

    return "\n".join(lines)
