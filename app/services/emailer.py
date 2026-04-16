import brevo_python
from brevo_python.api import transactional_emails_api
from brevo_python.model.send_smtp_email import SendSmtpEmail
from brevo_python.model.send_smtp_email_sender import SendSmtpEmailSender
from brevo_python.model.send_smtp_email_to import SendSmtpEmailTo
from app.config import settings

RECIPIENTS = [settings.alert_email_faisal, settings.alert_email_aftab]


def _get_api():
    configuration = brevo_python.Configuration()
    configuration.api_key["api-key"] = settings.brevo_api_key
    client = brevo_python.ApiClient(configuration)
    return transactional_emails_api.TransactionalEmailsApi(client)


def send_alert_email(subject: str, body: str, recipients: list[str] = None) -> bool:
    to_list = recipients or RECIPIENTS
    try:
        api = _get_api()
        email = SendSmtpEmail(
            sender=SendSmtpEmailSender(name="Tangier Agent", email=settings.from_email),
            to=[SendSmtpEmailTo(email=addr) for addr in to_list],
            subject=f"[Tangier Agent] {subject}",
            text_content=body
        )
        api.send_transac_email(email)
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
