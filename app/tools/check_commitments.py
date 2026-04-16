from app.database import db
from datetime import date


def check_commitments() -> str:
    commitments = db.table("commitments")\
        .select("*, contacts(name, company)")\
        .eq("status", "open")\
        .order("due_date")\
        .execute()

    if not commitments.data:
        return "No open commitments."

    lines = [f"OPEN COMMITMENTS — {date.today().isoformat()}", ""]
    for c in commitments.data:
        due = c.get("due_date", "no date")
        overdue = " [OVERDUE]" if due and due < date.today().isoformat() else ""
        contact = c.get("contacts") or {}
        contact_str = f" — {contact.get('name', '')} ({contact.get('company', '')})" if contact else ""
        lines.append(f"  {overdue}{c['description']}{contact_str} — due {due} — promised by {c['promised_by']}")

    return "\n".join(lines)
