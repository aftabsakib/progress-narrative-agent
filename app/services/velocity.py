from datetime import date
from typing import Optional
from app.config import settings


def calculate_days_stalled(last_touched: Optional[date]) -> int:
    if last_touched is None:
        return 999
    return (date.today() - last_touched).days


def is_below_outreach_target(count: int, target: int = 10) -> bool:
    return count < target


def get_aaep_days_remaining(aaep_window_end: str = None) -> int:
    end_str = aaep_window_end or settings.aaep_window_end
    end = date.fromisoformat(end_str)
    return (end - date.today()).days


def get_velocity_summary() -> dict:
    from app.database import db
    from datetime import timedelta

    today = date.today()
    yesterday = today - timedelta(days=1)

    activities_today = db.table("activities")\
        .select("id")\
        .eq("date", today.isoformat())\
        .execute()

    activities_yesterday = db.table("activities")\
        .select("id")\
        .eq("date", yesterday.isoformat())\
        .execute()

    activities_two_days_ago = db.table("activities")\
        .select("id")\
        .eq("date", (today - timedelta(days=2)).isoformat())\
        .execute()

    contacts = db.table("contacts")\
        .select("*")\
        .eq("tier", "1")\
        .execute()

    stalled_tier1 = [
        c for c in contacts.data
        if calculate_days_stalled(
            date.fromisoformat(c["last_touched"]) if c.get("last_touched") else None
        ) >= 5
    ]

    us_contacts = db.table("contacts")\
        .select("id")\
        .eq("pipeline_track", "us_side")\
        .execute()
    us_ids = [c["id"] for c in us_contacts.data]

    two_days_ago = today - timedelta(days=2)

    def _count_us_touches(day):
        by_type = db.table("activities")\
            .select("id")\
            .eq("date", day.isoformat())\
            .eq("activity_type", "us_side_outreach")\
            .execute()
        if us_ids:
            by_contact = db.table("activities")\
                .select("id")\
                .eq("date", day.isoformat())\
                .in_("contact_id", us_ids)\
                .execute()
            return len({a["id"] for a in by_type.data} | {a["id"] for a in by_contact.data})
        return len(by_type.data)

    us_touch_count = _count_us_touches(today)
    us_touch_count_yesterday = _count_us_touches(yesterday)
    us_touch_count_two_days_ago = _count_us_touches(two_days_ago)

    metrics = db.table("velocity_metrics")\
        .select("*")\
        .order("date", desc=True)\
        .limit(1)\
        .execute()

    inmails_remaining = metrics.data[0]["inmails_remaining"] if metrics.data else 45

    count_today = len(activities_today.data)
    count_yesterday = len(activities_yesterday.data)

    return {
        "outreach_count_today": count_today,
        "outreach_count_yesterday": count_yesterday,
        "outreach_count_two_days_ago": len(activities_two_days_ago.data),
        "target": 10,
        "on_target": count_today >= 10,
        "stalled_tier1": stalled_tier1,
        "us_side_touches_today": us_touch_count,
        "us_side_touches_yesterday": us_touch_count_yesterday,
        "us_side_touches_two_days_ago": us_touch_count_two_days_ago,
        "inmails_remaining": inmails_remaining,
        "aaep_days_remaining": get_aaep_days_remaining(),
    }
