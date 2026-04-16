import sendgrid
from sendgrid.helpers.mail import Mail, To
from app.config import settings

sg = sendgrid.SendGridAPIClient(api_key=settings.sendgrid_api_key)

RECIPIENTS = [settings.alert_email_faisal, settings.alert_email_aftab]


def send_alert_email(subject: str, body: str, recipients: list[str] = None) -> bool:
    to_list = recipients or RECIPIENTS
    message = Mail(
        from_email=settings.from_email,
        to_emails=[To(email) for email in to_list],
        subject=f"[Tangier Agent] {subject}",
        plain_text_content=body
    )
    try:
        sg.send(message)
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False


def send_daily_brief_email(brief_body: str) -> bool:
    return send_alert_email("Daily Brief", brief_body)


def send_alert_emails(alerts: list[dict]) -> None:
    """Send emails for unnotified alerts."""
    from app.database import db
    for alert in alerts:
        if not alert.get("emailed"):
            subject = f"[{alert['severity'].upper()}] {alert['type'].replace('_', ' ').title()}"
            sent = send_alert_email(subject, alert["message"])
            if sent and alert.get("id"):
                db.table("alerts").update({"emailed": True}).eq("id", alert["id"]).execute()
