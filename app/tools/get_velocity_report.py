from app.services.velocity import get_velocity_summary, calculate_days_stalled
from app.database import db
from datetime import date, timedelta


def _day_comparison() -> tuple[int, int]:
    today = date.today()
    yesterday = today - timedelta(days=1)
    today_count = db.table("activities")\
        .select("id")\
        .eq("date", today.isoformat())\
        .execute()
    yesterday_count = db.table("activities")\
        .select("id")\
        .eq("date", yesterday.isoformat())\
        .execute()
    return len(today_count.data), len(yesterday_count.data)


def _us_linkedin_count() -> int:
    today = date.today()
    result = db.table("activities")\
        .select("id")\
        .gte("date", (today - timedelta(days=7)).isoformat())\
        .eq("activity_type", "us_side_outreach")\
        .execute()
    return len(result.data)


def get_velocity_report() -> str:
    v = get_velocity_summary()
    today_count, yesterday_count = _day_comparison()
    us_linkedin = _us_linkedin_count()

    if yesterday_count == 0:
        trend = "no activity yesterday"
    elif today_count > yesterday_count:
        diff = today_count - yesterday_count
        trend = f"up {diff} vs yesterday"
    elif today_count < yesterday_count:
        diff = yesterday_count - today_count
        trend = f"down {diff} vs yesterday"
    else:
        trend = "same as yesterday"

    lines = [
        f"VELOCITY REPORT — {date.today().isoformat()}",
        "",
        f"Outreach today:      {v['outreach_count_today']}/{v['target']} {'ON TARGET' if v['on_target'] else 'BELOW TARGET'}",
        f"Yesterday:           {yesterday_count} activities — {trend}",
        f"AAEP window:         {v['aaep_days_remaining']} days remaining",
        f"InMails available:   {v['inmails_remaining']}",
        f"U.S.-side today:     {v['us_side_touches_today']} touches (yesterday: {v['us_side_touches_yesterday']})",
        f"US LinkedIn (7d):    {us_linkedin} outreaches {'— ZERO this week' if us_linkedin == 0 else ''}",
        "",
        f"TIER 1 STALLED ({len(v['stalled_tier1'])}):",
    ]

    for contact in v["stalled_tier1"]:
        last = date.fromisoformat(contact["last_touched"]) if contact.get("last_touched") else None
        days = calculate_days_stalled(last)
        lines.append(f"  - {contact['name']} ({contact.get('company', '')}) — {days} days")

    if not v["stalled_tier1"]:
        lines.append("  None — all Tier 1 entities touched within 5 days.")

    return "\n".join(lines)
