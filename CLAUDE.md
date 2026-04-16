# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

The Progress Tracking and Narrative Agent for Tangier. A chief-of-staff agent that monitors organizational velocity, tracks corridor construction progress, holds Faisal and Aftab accountable to commitments, and generates daily narrative through 11 MCP tools and email alerts.

## Running the Server

```bash
pip install -r requirements.txt
cp .env.example .env  # fill in values
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Running Tests

```bash
pytest tests/ -v
pytest tests/test_extractor.py -v  # single file
```

## Seeding Historical Data

Run once before go-live:
```bash
python scripts/seed.py
```

## Architecture

FastAPI app with MCP SSE transport. All 11 tools live in `app/tools/`. Services in `app/services/` handle extraction (Claude API), embedding (OpenAI), narrative generation (Claude API), velocity calculation, alert evaluation, and email dispatch (SendGrid). State is shared via Supabase. Both Faisal and Aftab connect via MCP from their Claude Code terminals.

## Key Design Decisions

- **Extraction**: Claude Sonnet extracts activities/commitments/contacts from any pasted text. Prompt in `app/services/extractor.py`.
- **Memory**: Activities are embedded (OpenAI text-embedding-3-small) and stored with pgvector. Similar past situations are retrieved during narrative generation.
- **Personality**: The Corridor Insider. Uses Tangier's vocabulary. Never softens a stall. Reads like Faisal's internal monologue. System prompt in `app/services/master_context.py`.
- **Alerts**: 14 triggers evaluated every 2 hours. Emails both faisal@tangier.us and community@evqlabs.com. Session hook surfaces pending alerts at the start of every Claude Code session.
- **Three strategic tests**: Every activity is scored: (1) makes outreach more effective, (2) advances Tier 1 relationship, (3) builds U.S.-side credibility. Activities scoring 0 are flagged.

## Phase Roadmap

- Phase 1 (current): Manual input, all 11 tools, email alerts, seeding
- Phase 2: GitHub CLI pull (`pull_github_notes` tool)
- Phase 3: Granola transcript ingestion
- Phase 4: Telegram analysis
