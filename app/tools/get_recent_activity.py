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

    # Deduplicate by description (same text logged twice from same transcript)
    seen_descriptions = set()
    unique_rows = []
    for r in rows.data:
        desc = r.get("description", "").strip()
        if desc not in seen_descriptions:
            seen_descriptions.add(desc)
            unique_rows.append(r)

    # Group by contact
    by_contact: dict = {}
    no_contact = []

    for r in unique_rows:
        contact = r.get("contact_name") or r.get("contact_id") or None
        description = r.get("description", "")
        who = r.get("created_by", "?")
        ts = r.get("created_at", "")[:16].replace("T", " ")

        entry = (who, description, ts)

        if contact:
            if contact not in by_contact:
                by_contact[contact] = []
            by_contact[contact].append(entry)
        else:
            no_contact.append(entry)

    lines = [f"## Activity Log — Last {hours}h ({len(unique_rows)} entries)", ""]

    if by_contact:
        for contact, entries in by_contact.items():
            lines.append(f"### {contact}")
            lines.append("")
            for who, description, ts in entries:
                lines.append(f"- **[{who}]** {description}")
                lines.append(f"  *{ts}*")
                lines.append("")

    if no_contact:
        lines.append("### Other Activity")
        lines.append("")
        for who, description, ts in no_contact:
            lines.append(f"- **[{who}]** {description}")
            lines.append(f"  *{ts}*")
            lines.append("")

    return "\n".join(lines)
