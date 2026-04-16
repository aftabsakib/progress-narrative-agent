from app.database import db
from app.models.schemas import CorrectEntryInput

TABLE_MAP = {
    "activity": "activities",
    "commitment": "commitments",
    "contact": "contacts",
    "artifact": "artifacts"
}


def correct_entry(input: CorrectEntryInput) -> str:
    table = TABLE_MAP.get(input.entry_type)
    if not table:
        return f"Unknown entry type: {input.entry_type}. Use: activity, commitment, contact, artifact."

    db.table(table).update({input.field: input.new_value}).eq("id", input.entry_id).execute()
    return f"Updated {input.entry_type} {input.entry_id}: {input.field} = {input.new_value}"
