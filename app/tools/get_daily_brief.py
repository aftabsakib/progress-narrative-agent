from app.services.narrator import generate_daily_brief
from app.database import db
from datetime import date


def get_daily_brief_tool(save: bool = True) -> str:
    brief = generate_daily_brief()
    if save:
        db.table("narratives").insert({
            "date": date.today().isoformat(),
            "type": "daily",
            "body": brief
        }).execute()
    return brief
