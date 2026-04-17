from app.database import db
from app.services.velocity import calculate_days_stalled
from datetime import date

STAGE_NAMES = {
    1: "Role Identification",
    2: "Role Packet / Initial Mandate",
    3: "Role Preparation",
    4: "Role Buy-in / Commitment",
    5: "Role Execution",
    6: "New Role Creation"
}

TIER_LABELS = {
    "1": "TIER 1 — Deep Strategic Pursuit",
    "2": "TIER 2 — Active Pipeline",
    "3": "TIER 3",
    "us_side": "US SIDE"
}


def _get_pending_artifacts(contact_id: str) -> str:
    artifacts = db.table("artifacts")\
        .select("type, sent_date, response_received")\
        .eq("contact_id", contact_id)\
        .eq("response_received", False)\
        .execute()
    if not artifacts.data:
        return ""
    types = [a["type"] for a in artifacts.data if a.get("sent_date")]
    if types:
        return f" [awaiting response: {', '.join(types)}]"
    return ""


def get_pipeline_snapshot() -> str:
    contacts = db.table("contacts")\
        .select("*")\
        .neq("status", "cadaver")\
        .order("tier")\
        .execute()

    lines = [f"PIPELINE SNAPSHOT — {date.today().isoformat()}", ""]
    current_tier = None

    for c in contacts.data:
        if c["tier"] != current_tier:
            current_tier = c["tier"]
            label = TIER_LABELS.get(current_tier, f"TIER {current_tier}")
            lines.append(f"\n{label}")

        last = date.fromisoformat(c["last_touched"]) if c.get("last_touched") else None
        days = calculate_days_stalled(last)
        stage = STAGE_NAMES.get(c.get("role_stage", 1), "Unknown")

        # Check for pending artifacts — don't flag as stalled if awaiting response
        pending = _get_pending_artifacts(c["id"])

        if pending:
            status_str = f" (awaiting response — {days}d){pending}"
        elif days >= 14:
            status_str = f" STALLED {days}d — needs touch"
        elif days >= 5:
            status_str = f" ({days}d — watch)"
        else:
            status_str = f" ({days}d ago)"

        lines.append(
            f"  {c['name']} — {c.get('company', '')} — "
            f"Stage {c.get('role_stage', 1)}: {stage}{status_str}"
        )

    return "\n".join(lines)
