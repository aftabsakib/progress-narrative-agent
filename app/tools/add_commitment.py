from app.database import db
from app.models.schemas import AddCommitmentInput


def add_commitment(input: AddCommitmentInput) -> str:
    contact_id = None
    if input.contact_name:
        result = db.table("contacts")\
            .select("id")\
            .ilike("name", f"%{input.contact_name}%")\
            .limit(1)\
            .execute()
        if result.data:
            contact_id = result.data[0]["id"]

    db.table("commitments").insert({
        "description": input.description,
        "due_date": input.due_date.isoformat() if input.due_date else None,
        "promised_by": input.promised_by,
        "contact_id": contact_id,
        "status": "open"
    }).execute()

    return f"Commitment logged: '{input.description}' — due {input.due_date or 'no date'} — {input.promised_by}."
