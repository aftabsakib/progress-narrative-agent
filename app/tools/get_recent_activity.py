from app.database import db


def get_recent_activity(hours: int = 24, limit: int = 20) -> str:
    from datetime import datetime, timezone, timedelta

    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    rows = db.table("activities") \
        .select("*") \
        .gte("created_at", since) \
        .order("created_at", desc=True) \
        .limit(limit) \
        .execute()

    if not rows.data:
        return f"No activities logged in the last {hours} hours."

    lines = [f"RECENT ACTIVITY (last {hours}h — {len(rows.data)} entries)", ""]
    for r in rows.data:
        ts = r.get("created_at", "")[:16].replace("T", " ")
        who = r.get("created_by", "unknown")
        activity_type = r.get("activity_type", "update")
        description = r.get("description") or r.get("raw_text", "")[:120]
        contact = r.get("contact_name", "")
        contact_str = f" [{contact}]" if contact else ""
        lines.append(f"  {ts} | {who}{contact_str} | {activity_type}: {description}")

    return "\n".join(lines)
