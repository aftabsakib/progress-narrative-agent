from app.database import db


def get_setting(key: str, default=None):
    result = db.table("agent_settings").select("value").eq("key", key).execute()
    if not result.data:
        return default
    val = result.data[0]["value"]
    if val == "true":
        return True
    if val == "false":
        return False
    return val


def set_setting(key: str, value) -> None:
    db.table("agent_settings").upsert(
        {"key": key, "value": str(value).lower()},
        on_conflict="key"
    ).execute()


def alerts_paused() -> bool:
    return get_setting("alerts_paused", default=False)
