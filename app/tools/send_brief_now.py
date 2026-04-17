from app.services.narrator import generate_daily_brief, generate_acceleration_brief
from app.services.emailer import send_daily_brief_email, send_acceleration_email
from app.tools.get_recent_activity import get_recent_activity


def send_brief_now(brief_type: str = "morning") -> str:
    if brief_type == "afternoon":
        brief = generate_acceleration_brief()
        sent = send_acceleration_email(brief)
        label = "Afternoon acceleration brief"
    else:
        brief = generate_daily_brief()
        activity_log = get_recent_activity(hours=24)
        full_email = f"{brief}\n\n---\n\nACTIVITY LOG (LAST 24H)\n\n{activity_log}"
        sent = send_daily_brief_email(full_email)
        label = "Morning brief"

    if sent:
        return f"{label} sent to faisal@tangier.us and et.am.sakib@gmail.com."
    return "Email failed to send — check Brevo sender verification for the FROM_EMAIL address."
