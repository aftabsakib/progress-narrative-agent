import anthropic
from app.config import settings
from app.services.master_context import MASTER_CONTEXT

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


def score_activity(description: str) -> str:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=MASTER_CONTEXT,
        messages=[{
            "role": "user",
            "content": f"Score this activity against Tangier's three tests (1 point each): (1) Makes outreach more effective, (2) Advances a Tier 1 relationship, (3) Builds U.S.-side credibility.\n\nActivity: {description}\n\nReturn: score (0-3), which tests passed, and one sentence of reasoning."
        }]
    )
    return response.content[0].text
