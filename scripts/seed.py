"""
One-time seeder for historical Tangier context.
Run once before go-live: python scripts/seed.py

Loads:
- Tier 1 contacts (8 entities)
- Known pipeline contacts
- Historical outreach state
- AAEP status trigger
"""
from app.database import db
from datetime import date


def seed_tier1_contacts():
    tier1 = [
        {"name": "G42", "company": "G42", "tier": "1", "pipeline_track": "global_south", "role_stage": 1, "status": "active"},
        {"name": "Humain", "company": "Humain", "tier": "1", "pipeline_track": "global_south", "role_stage": 1, "status": "active"},
        {"name": "STC", "company": "STC", "tier": "1", "pipeline_track": "global_south", "role_stage": 1, "status": "active"},
        {"name": "Zain", "company": "Zain", "tier": "1", "pipeline_track": "global_south", "role_stage": 1, "status": "active"},
        {"name": "Ooredoo", "company": "Ooredoo", "tier": "1", "pipeline_track": "global_south", "role_stage": 1, "status": "active"},
        {"name": "QAI", "company": "QAI", "tier": "1", "pipeline_track": "global_south", "role_stage": 1, "status": "active"},
        {"name": "Omantel", "company": "Omantel", "tier": "1", "pipeline_track": "global_south", "role_stage": 2, "status": "active"},
        {"name": "e&", "company": "e&", "tier": "1", "pipeline_track": "global_south", "role_stage": 1, "status": "active"},
    ]
    for c in tier1:
        db.table("contacts").insert(c).execute()
    print(f"Seeded {len(tier1)} Tier 1 contacts.")


def seed_active_pipeline():
    pipeline = [
        {
            "name": "Banglalink",
            "company": "Banglalink",
            "tier": "2",
            "pipeline_track": "global_south",
            "role_stage": 2,
            "status": "active",
            "notes": "Current central case. Proposal being rebuilt. Working group test target."
        },
        {
            "name": "True Corporation",
            "company": "True Corporation",
            "tier": "1",
            "pipeline_track": "global_south",
            "role_stage": 1,
            "status": "active",
            "notes": "Connected through wealthy Thai family. Separate InMail opportunity."
        },
        {
            "name": "Chaudhry Group",
            "company": "Chaudhry Group",
            "tier": "2",
            "pipeline_track": "global_south",
            "role_stage": 1,
            "status": "active",
            "notes": "Nepal. Rahul contacted but not fully engaged."
        },
    ]
    for c in pipeline:
        db.table("contacts").insert(c).execute()
    print(f"Seeded {len(pipeline)} active pipeline contacts.")


def seed_velocity_baseline():
    db.table("velocity_metrics").insert({
        "date": date.today().isoformat(),
        "outreach_count": 0,
        "target": 10,
        "tier1_touches": 0,
        "us_side_touches": 0,
        "inmails_sent": 0,
        "inmails_remaining": 45,
        "aaep_days_remaining": 74
    }).execute()
    print("Seeded velocity baseline.")


def seed_aaep_intelligence_trigger():
    db.table("intelligence_triggers").insert({
        "date": "2026-04-01",
        "type": "aaep_launch",
        "description": "AAEP preset consortium path went live April 1, 2026. 90-day window. Call for proposals open.",
        "actioned": False
    }).execute()
    print("Seeded AAEP launch trigger.")


if __name__ == "__main__":
    print("Seeding Tangier historical context...")
    seed_tier1_contacts()
    seed_active_pipeline()
    seed_velocity_baseline()
    seed_aaep_intelligence_trigger()
    print("Seed complete. Run get_daily_brief to verify.")
