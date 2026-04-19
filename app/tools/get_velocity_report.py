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

    today_str = date.today().isoformat()
    tc = v["outreach_count_today"]
    yc = v["outreach_count_yesterday"]
    target = v["target"]
    us_today = v["us_side_touches_today"]
    us_yesterday = v["us_side_touches_yesterday"]
    us_two_days_ago = v["us_side_touches_two_days_ago"]
    aaep = v["aaep_days_remaining"]

    # Outreach line
    if tc == 0:
        outreach_line = f"Zero outreach today against a target of {target}."
    elif tc >= target:
        outreach_line = f"{tc} outreaches today. Target is {target}. On track."
    else:
        outreach_line = f"{tc} outreaches today against a target of {target}."

    # Day comparison
    if yc == 0:
        comparison_line = "No activity logged yesterday."
    elif tc == 0 and yc > 0:
        comparison_line = f"Yesterday was {yc}. The drop is total, not partial."
    elif tc > yc:
        comparison_line = f"Yesterday was {yc}. Up {tc - yc}."
    elif tc < yc:
        comparison_line = f"Yesterday was {yc}. Down {yc - tc}."
    else:
        comparison_line = f"Yesterday was {yc}. Same pace."

    # US-side: show 3-day trend to surface progress
    if us_yesterday > us_two_days_ago:
        us_trend = f"Up from {us_two_days_ago} the day before. Progress."
    elif us_yesterday == 0 and us_two_days_ago == 0:
        us_trend = "Zero for at least two days running."
    else:
        us_trend = f"{us_two_days_ago} the day before."

    if us_today == 0:
        us_line = f"U.S.-side: zero today. Yesterday was {us_yesterday}. {us_trend}"
    else:
        us_line = f"U.S.-side: {us_today} today. Yesterday was {us_yesterday}. {us_trend}"

    aaep_line = f"AAEP window closes in {aaep} days."

    lines = [
        f"Velocity — {today_str}",
        "",
        outreach_line,
        comparison_line,
        "",
        us_line,
        "",
        aaep_line,
    ]

    if v["stalled_tier1"]:
        lines += ["", f"Tier 1 ({len(v['stalled_tier1'])} not yet touched in the system):"]
        for contact in v["stalled_tier1"]:
            last = date.fromisoformat(contact["last_touched"]) if contact.get("last_touched") else None
            days = calculate_days_stalled(last)
            label = "not yet logged" if days >= 999 else f"{days} days"
            lines.append(f"  {contact['name']} ({contact.get('company', '')}) — {label}.")
    else:
        lines += ["", "No Tier 1 stalls. All entities touched within five days."]

    return "\n".join(lines)
