import pytest
from unittest.mock import MagicMock, patch
from app.services.extractor import extract_from_text


@pytest.mark.asyncio
async def test_extract_activities_from_text():
    sample_text = """
    Called Michael today. He said he would send the LOI by Thursday.
    Also followed up with Banglalink — they are interested in the working group.
    Sent the AAEP intelligence brief to 12 contacts.
    """
    with patch("app.services.extractor.anthropic_client") as mock_client:
        mock_client.messages.create = MagicMock(return_value=type('R', (), {
            'content': [type('C', (), {
                'text': '{"activities": ["Called Michael", "Followed up with Banglalink", "Sent AAEP intelligence brief to 12 contacts"], "commitments": [{"description": "Michael sends LOI", "due_date": "2026-04-17", "promised_by": "Michael"}], "contacts_mentioned": ["Michael", "Banglalink"], "intelligence_triggers": []}'
            })()]
        })())
        result = await extract_from_text(sample_text)

    assert len(result["activities"]) == 3
    assert len(result["commitments"]) == 1
    assert result["commitments"][0]["promised_by"] == "Michael"
    assert "Banglalink" in result["contacts_mentioned"]
