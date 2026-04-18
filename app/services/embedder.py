from openai import OpenAI
from app.config import settings

openai_client = OpenAI(api_key=settings.openai_api_key, timeout=10.0)


def embed_text(text: str) -> list[float]:
    """Generate 1536-dimension embedding using OpenAI text-embedding-3-small."""
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


def find_similar_activities(embedding: list[float], limit: int = 5) -> list[dict]:
    """Find semantically similar past activities using pgvector cosine similarity."""
    from app.database import db
    result = db.rpc(
        "match_activities",
        {"query_embedding": embedding, "match_count": limit}
    ).execute()
    return result.data
