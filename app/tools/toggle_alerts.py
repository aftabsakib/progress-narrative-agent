from app.services.settings_service import set_setting, alerts_paused


def toggle_alerts(paused: bool) -> str:
    set_setting("alerts_paused", paused)
    if paused:
        return "Alerts paused. No alert emails will be sent and session alerts are suppressed until you resume."
    return "Alerts resumed. Alert checks and emails are active again."
