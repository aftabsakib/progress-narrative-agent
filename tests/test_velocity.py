import pytest
from datetime import date, timedelta
from app.services.velocity import (
    calculate_days_stalled,
    is_below_outreach_target,
    get_aaep_days_remaining
)


def test_days_stalled_with_recent_touch():
    last_touched = date.today() - timedelta(days=3)
    assert calculate_days_stalled(last_touched) == 3


def test_days_stalled_with_no_touch():
    assert calculate_days_stalled(None) == 999


def test_below_outreach_target():
    assert is_below_outreach_target(8, target=10) is True
    assert is_below_outreach_target(10, target=10) is False
    assert is_below_outreach_target(12, target=10) is False


def test_aaep_days_remaining():
    end = date.today() + timedelta(days=74)
    days = get_aaep_days_remaining(end.isoformat())
    assert days == 74
