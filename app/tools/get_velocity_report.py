from app.services.velocity import get_velocity_summary, calculate_days_stalled
from app.database import db
from datetime import date, timedelta


def _week_comparison() -> tuple[int, int]:
    today = date.today()
    this_week = db.table("activities")\
        .select("id")\
        .gte("date", (today - timedelta(days=7)).isoformat())\
        .execute()
    last_week = db.table("activities")\
        .select("id")\
        .gte("date", (today - timedelta(days=14)).isoformat())\
        .lt("date", (today - timedelta(days=7)).isoformat())\
        .execute()
    return len(this_week.data), len(last_week.data)


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
    this_week, last_week = _week_comparison()
    us_linkedin = _us_linkedin_count()

    if last_week == 0:
        trend = "no prior week data"
    elif this_week > last_week:
        pct = round(((this_week - last_week) / last_week) * 100)
        trend = f"UP {pct}% vs last week"
    elif this_week < last_week:
        pct = round(((last_week - this_week) / last_week) * 100)
        trend = f"DOWN {pct}% vs last week"
    else:
        trend = "same as last week"

    lines = [
        f"VELOCITY REPORT — {date.today().isoformat()}",
        "",
        f"Outreach today:      {v['outreach_count_today']}/{v['target']} {'ON TARGET' if v['on_target'] else 'BELOW TARGET'}",
        f"This week vs last:   {this_week} activities this week / {last_week} last week — {trend}",
        f"AAEP window:         {v['aaep_days_remaining']} days remaining",
        f"InMails available:   {v['inmails_remaining']}",
        f"U.S.-side today:     {v['us_side_touches_today']} touches",
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
