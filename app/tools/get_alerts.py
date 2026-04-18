from app.database import db


def get_alerts() -> str:
    from app.services.alerts import run_all_alert_checks
    from app.services.emailer import send_alert_emails
    from app.services.settings_service import alerts_paused

    if alerts_paused():
        return "Alerts are paused. Say 'resume alerts' to turn them back on."

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
