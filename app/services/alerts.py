from datetime import date
from typing import Optional


def evaluate_aaep_alert(days_remaining: int) -> Optional[dict]:
    if days_remaining <= 14:
        return {
            "type": "aaep_window",
            "message": f"AAEP window closes in {days_remaining} days. Maximum urgency.",
            "severity": "critical"
        }
    if days_remaining <= 30:
        return {
            "type": "aaep_window",
            "message": f"AAEP window closes in {days_remaining} days.",
            "severity": "warning"
        }
    if days_remaining <= 60:
        return {
            "type": "aaep_window",
            "message": f"AAEP window closes in {days_remaining} days.",
            "severity": "info"
        }
    return None


def evaluate_outreach_alert(today_count: int, yesterday_count: int, target: int = 10) -> Optional[dict]:
    if today_count < target and yesterday_count < target:
        return {
            "type": "outreach_below_target",
            "message": f"Outreach below target for 2 consecutive days. Today: {today_count}, Yesterday: {yesterday_count}. Target: {target}.",
            "severity": "warning"
        }
    return None


def evaluate_tier1_stall_alert(contact: dict, days_stalled: int) -> Optional[dict]:
    if days_stalled >= 5:
        return {
            "type": "tier1_stall",
            "message": f"{contact['name']} ({contact.get('company', '')}) — Tier 1 — not touched in {days_stalled} days.",
            "severity": "warning",
            "contact_id": contact["id"]
        }
    return None


def evaluate_us_side_alert() -> Optional[dict]:
    from app.database import db
    contacts = db.table("contacts").select("id").eq("pipeline_track", "us_side").execute()
    if not contacts.data:
        return {
            "type": "us_side_zero",
            "message": "U.S.-side outreach is at zero. No contacts mapped yet. The lever that makes everything else fall into line hasn't been pulled.",
            "severity": "warning"
        }
    return None


def evaluate_inmail_alert(inmails_remaining: int, days_since_last_use: int) -> Optional[dict]:
    if days_since_last_use >= 7 and inmails_remaining > 0:
        return {
            "type": "inmail_unused",
            "message": f"{inmails_remaining} InMails available, none used in {days_since_last_use} days. Tier 1 targets are waiting.",
            "severity": "warning"
        }
    return None


def run_all_alert_checks() -> list[dict]:
    """Run all threshold checks and queue new alerts in the database."""
    from app.database import db
    from app.services.velocity import get_aaep_days_remaining, calculate_days_stalled

    alerts = []

    aaep_alert = evaluate_aaep_alert(get_aaep_days_remaining())
    if aaep_alert:
        alerts.append(aaep_alert)

    us_alert = evaluate_us_side_alert()
    if us_alert:
        alerts.append(us_alert)

    tier1 = db.table("contacts").select("*").eq("tier", "1").execute()
    for contact in tier1.data:
        last = date.fromisoformat(contact["last_touched"]) if contact.get("last_touched") else None
        days = calculate_days_stalled(last)
        alert = evaluate_tier1_stall_alert(contact, days)
        if alert:
            alerts.append(alert)

    overdue = db.table("commitments")\
        .select("*, contacts(name, company)")\
        .eq("status", "open")\
        .lt("due_date", date.today().isoformat())\
        .execute()
    for c in overdue.data:
        alerts.append({
            "type": "commitment_overdue",
            "message": f"Overdue: '{c['description']}' — promised by {c['promised_by']}.",
            "severity": "warning",
            "contact_id": c.get("contact_id")
        })

    for alert in alerts:
        db.table("alerts").insert({
            "type": alert["type"],
            "message": alert["message"],
            "severity": alert.get("severity", "info"),
            "contact_id": alert.get("contact_id")
        }).execute()

    return alerts
