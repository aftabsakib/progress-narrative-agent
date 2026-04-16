from app.database import db
from datetime import date


def get_artifact_status() -> str:
    artifacts = db.table("artifacts")\
        .select("*, contacts(name, company)")\
        .order("produced_date", desc=True)\
        .execute()

    if not artifacts.data:
        return "No artifacts tracked yet."

    sent = [a for a in artifacts.data if a.get("sent_date")]
    responded = [a for a in artifacts.data if a.get("response_received")]

    if sent:
        conversion = f"{round(len(responded)/len(sent)*100)}%"
    else:
        conversion = "No artifacts sent yet."

    lines = [
        f"ARTIFACT STATUS — {date.today().isoformat()}",
        f"Total produced: {len(artifacts.data)} | Sent: {len(sent)} | Responses: {len(responded)}",
        f"Conversion (sent to response): {conversion}",
        ""
    ]
    for a in artifacts.data[:10]:
        contact = a.get("contacts") or {}
        status = "RESPONDED" if a["response_received"] else ("SENT" if a.get("sent_date") else "PRODUCED")
        lines.append(f"  [{status}] {a['type']} — {contact.get('name', 'unknown')} ({contact.get('company', '')}) — {a.get('produced_date', '')}")

    return "\n".join(lines)
