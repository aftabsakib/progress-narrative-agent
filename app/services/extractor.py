import anthropic
import json
import re
from app.config import settings

anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

EXTRACTION_SYSTEM_PROMPT = """You are extracting structured data from Tangier's organizational activity logs.

Tangier connects U.S. frontier AI with Global South principals — telcos, sovereign wealth funds, national champions. Every action is measured against three tests: does it make outreach more effective, advance a Tier 1 relationship, or build U.S.-side credibility?

Extract from the provided text:

1. activities: list of discrete actions taken. Each must be:
   - A complete, human-readable sentence describing exactly what happened
   - Specific enough to stand alone without context
   - Tagged with action_type: one of outreach, call, proposal_sent, commitment_made, strategic_reframing, research, asset_created, follow_up, relationship_touch, us_side_outreach, internal
   - Tagged with contact_name: the single most relevant contact or company this activity is about (e.g. "Banglalink", "Ekaraj", "True Corporation"). Null if purely internal with no external contact.
   - Example good description: "Faisal sent revised two-pager to El Kope (Cell C CFO) correcting Tangier's positioning from AI vendor to governed operator"
   - Example bad description: "update" or "sent document" or "position metrics snapshot recorded"

2. commitments: list of {description, due_date (YYYY-MM-DD or null), promised_by (person name), contact_name (if applicable)}

3. contacts_mentioned: list of contact/company names referenced

4. intelligence_triggers: list of {type, description} for AAEP news, policy changes, leadership changes, earnings calls, regulatory updates

5. strategic_reframings: list of strings describing any strategic positioning changes, new frameworks articulated, or messaging updates discussed — these are important organizational learning moments

Return valid JSON only. No explanation.

JSON structure:
{
  "activities": [{"description": "...", "action_type": "...", "contact_name": "...or null"}],
  "commitments": [{"description": "...", "due_date": "...", "promised_by": "...", "contact_name": "..."}],
  "contacts_mentioned": ["..."],
  "intelligence_triggers": [{"type": "...", "description": "..."}],
  "strategic_reframings": ["..."]
}"""


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
