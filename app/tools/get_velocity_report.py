from app.services.velocity import get_velocity_summary, calculate_days_stalled
from datetime import date


def get_velocity_report() -> str:
    v = get_velocity_summary()
    lines = [
        f"VELOCITY REPORT — {date.today().isoformat()}",
        "",
        f"Outreach today: {v['outreach_count_today']}/{v['target']} {'ON TARGET' if v['on_target'] else 'BELOW TARGET'}",
        f"AAEP window: {v['aaep_days_remaining']} days remaining",
        f"InMails available: {v['inmails_remaining']}",
        f"U.S.-side touches today: {v['us_side_touches_today']}",
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
