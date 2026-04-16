import anthropic
import json
import re
from app.config import settings

anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

EXTRACTION_SYSTEM_PROMPT = """You are extracting structured data from Tangier's organizational activity logs.

Tangier is corridor infrastructure connecting U.S. frontier AI with Global South principals — telcos, sovereign wealth funds, national champions. Every action is measured against three tests: does it make outreach more effective, advance a Tier 1 relationship, or build U.S.-side credibility?

Extract from the provided text:
1. activities: list of discrete actions taken (strings)
2. commitments: list of {description, due_date (YYYY-MM-DD or null), promised_by (person name)}
3. contacts_mentioned: list of contact/company names referenced
4. intelligence_triggers: list of {type, description} for AAEP news, policy changes, leadership changes, earnings calls

Return valid JSON only. No explanation."""


async def extract_from_text(text: str) -> dict:
    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=EXTRACTION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Extract structured data from this text:\n\n{text}"}]
    )
    raw = response.content[0].text
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r'```(?:json)?\n(.*?)\n```', raw, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise ValueError(f"Could not parse extraction response: {raw}")
