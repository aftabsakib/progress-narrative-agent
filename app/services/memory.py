from app.services.embedder import embed_text, find_similar_activities


def retrieve_similar_activities(context: str, limit: int = 5, min_similarity: float = 0.72) -> list[dict]:
    """Embed context text and return semantically similar past activities."""
    embedding = embed_text(context)
    results = find_similar_activities(embedding, limit=limit)
    return [r for r in results if r.get("similarity", 0) >= min_similarity]


def format_historical_parallels(activities: list[dict]) -> str:
    if not activities:
        return "None on record."
    lines = []
    for a in activities:
        sim_pct = round(a.get("similarity", 0) * 100)
        lines.append(f"- [{a['date']}] {a['description']} ({sim_pct}% match)")
    return "\n".join(lines)


def get_parallels_for_stalled_contacts(stalled: list[dict]) -> str:
    """
    Given a list of stalled contacts (each with name, company, role_stage, days_stalled),
    retrieve historical parallels for the top 3 most stalled and return a formatted block.
    """
    if not stalled:
        return "None."

    # Focus on top 3 most stalled to limit API calls
    top = sorted(stalled, key=lambda c: c.get("days_stalled") or 0, reverse=True)[:3]

    sections = []
    for contact in top:
        name = contact.get("name", "unknown")
        company = contact.get("company", "")
        stage = contact.get("role_stage", 1)
        days = contact.get("days_stalled") or 0

        query = (
            f"Tier 1 contact stalled at stage {stage}, no movement for {days} days. "
            f"Contact: {name}, {company}."
        )
        similar = retrieve_similar_activities(query, limit=3)
        formatted = format_historical_parallels(similar)
        sections.append(f"{name} (Stage {stage}, {days}d stalled):\n{formatted}")

    return "\n\n".join(sections)
