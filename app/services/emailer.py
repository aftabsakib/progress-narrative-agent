import markdown as md
import brevo_python
from brevo_python.api import transactional_emails_api
from brevo_python.models.send_smtp_email import SendSmtpEmail
from brevo_python.models.send_smtp_email_sender import SendSmtpEmailSender
from brevo_python.models.send_smtp_email_to import SendSmtpEmailTo
from app.config import settings

RECIPIENTS = [settings.alert_email_faisal, settings.alert_email_aftab]

_HTML_WRAPPER = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: Georgia, serif; font-size: 15px; color: #1a1a1a; max-width: 680px; margin: 0 auto; padding: 24px; }}
  h1, h2, h3 {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #111; margin-top: 24px; margin-bottom: 6px; }}
  h1 {{ font-size: 20px; border-bottom: 2px solid #111; padding-bottom: 6px; }}
  h2 {{ font-size: 17px; }}
  h3 {{ font-size: 15px; }}
  p {{ margin: 8px 0; line-height: 1.6; }}
  ul, ol {{ margin: 6px 0; padding-left: 20px; }}
  li {{ margin: 4px 0; line-height: 1.5; }}
  strong {{ font-weight: 700; }}
  hr {{ border: none; border-top: 1px solid #ccc; margin: 20px 0; }}
  pre {{ background: #f5f5f5; padding: 12px; font-size: 13px; white-space: pre-wrap; }}
</style>
</head>
<body>
{content}
</body>
</html>"""


def _to_html(text: str) -> str:
    body = md.markdown(text, extensions=["nl2br", "sane_lists"])
    return _HTML_WRAPPER.format(content=body)


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
            html_content=_to_html(body)
        )
        api.send_transac_email(email)
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False


def send_daily_brief_email(brief_body: str) -> bool:
    return send_alert_email("Morning Brief", brief_body)


def send_acceleration_email(body: str) -> bool:
    return send_alert_email("Afternoon Acceleration", body)


def send_alert_emails(alerts: list[dict]) -> None:
    """Send emails for unnotified alerts."""
    from app.database import db
    for alert in alerts:
        if not alert.get("emailed"):
            subject = f"[{alert['severity'].upper()}] {alert['type'].replace('_', ' ').title()}"
            sent = send_alert_email(subject, alert["message"])
            if sent and alert.get("id"):
                db.table("alerts").update({"emailed": True}).eq("id", alert["id"]).execute()
