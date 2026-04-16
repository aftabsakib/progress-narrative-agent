import pytest
from datetime import date, timedelta
from app.services.alerts import evaluate_aaep_alert, evaluate_outreach_alert


def test_aaep_alert_critical():
    alert = evaluate_aaep_alert(days_remaining=14)
    assert alert is not None
    assert alert["severity"] == "critical"


def test_aaep_alert_warning():
    alert = evaluate_aaep_alert(days_remaining=30)
    assert alert is not None
    assert alert["severity"] == "warning"


def test_aaep_no_alert():
    alert = evaluate_aaep_alert(days_remaining=75)
    assert alert is None


def test_outreach_alert_below_target():
    alert = evaluate_outreach_alert(today_count=7, yesterday_count=8, target=10)
    assert alert is not None


def test_outreach_no_alert():
    alert = evaluate_outreach_alert(today_count=11, yesterday_count=10, target=10)
    assert alert is None
