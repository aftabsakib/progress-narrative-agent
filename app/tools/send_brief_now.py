from app.services.narrator import generate_daily_brief
from app.services.emailer import send_daily_brief_email
from app.tools.get_recent_activity import get_recent_activity


def send_brief_now() -> str:
    brief = generate_daily_brief()
    activity_log = get_recent_activity(hours=24)
    full_email = f"{brief}\n\n---\n\nACTIVITY LOG (LAST 24H)\n\n{activity_log}"
    sent = send_daily_brief_email(full_email)
    if sent:
        return "Daily brief sent to faisal@tangier.us and et.am.sakib@gmail.com."
    return "Email failed to send — check Brevo sender verification for office@tangier.us."
