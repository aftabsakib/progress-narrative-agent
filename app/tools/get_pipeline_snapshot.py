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
    "us_side": "US SIDE — Not Yet Started"
}


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
        stall_flag = f" *** STALLED {days}d ***" if days >= 5 else f" ({days}d ago)"
        lines.append(f"  {c['name']} — {c.get('company', '')} — Stage {c.get('role_stage', 1)}: {stage}{stall_flag}")

    return "\n".join(lines)
