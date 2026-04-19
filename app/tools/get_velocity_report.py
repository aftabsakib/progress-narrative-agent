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
    aaep = v["aaep_days_remaining"]
    inmails = v["inmails_remaining"]

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

    # US-side line
    if us_today == 0 and us_yesterday == 0:
        us_line = "U.S.-side outreach is at zero. It has been zero for at least two days."
    elif us_today == 0:
        us_line = f"U.S.-side touches are zero today. Yesterday was {us_yesterday}. The lane needs to run every day."
    elif us_today > us_yesterday:
        us_line = f"U.S.-side: {us_today} today, up from {us_yesterday} yesterday."
    else:
        us_line = f"U.S.-side: {us_today} today, {us_yesterday} yesterday."

    # InMail line
    inmail_line = f"{inmails} InMails remain. The inventory is not the problem. The activity is." if inmails > 0 else "InMails exhausted."

    # AAEP line
    aaep_line = f"AAEP window closes in {aaep} days."

    lines = [
        f"Velocity — {today_str}",
        "",
        outreach_line,
        comparison_line,
        "",
        us_line,
        "",
        inmail_line,
        aaep_line,
    ]

    if v["stalled_tier1"]:
        lines += ["", f"Tier 1 stalled ({len(v['stalled_tier1']):}):"]
        for contact in v["stalled_tier1"]:
            last = date.fromisoformat(contact["last_touched"]) if contact.get("last_touched") else None
            days = calculate_days_stalled(last)
            lines.append(f"  {contact['name']} ({contact.get('company', '')}) — {days} days.")
    else:
        lines += ["", "No Tier 1 stalls. All entities touched within five days."]

    return "\n".join(lines)
