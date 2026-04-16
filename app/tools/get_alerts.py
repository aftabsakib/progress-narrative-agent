from app.database import db


def get_alerts() -> str:
    from app.services.alerts import run_all_alert_checks
    from app.services.emailer import send_alert_emails

    run_all_alert_checks()

    pending = db.table("alerts")\
        .select("*")\
        .eq("actioned", False)\
        .order("severity")\
        .order("created_at", desc=True)\
        .execute()

    send_alert_emails(pending.data)

    if not pending.data:
        return "No pending alerts."

    lines = [f"ALERTS ({len(pending.data)} pending)", ""]
    for a in pending.data:
        lines.append(f"  [{a['severity'].upper()}] {a['message']}")

    return "\n".join(lines)
