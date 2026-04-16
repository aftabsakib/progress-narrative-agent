# Progress Tracking and Narrative Agent — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a chief-of-staff agent that tracks Tangier's organizational velocity, accountability, and corridor construction progress — and narrates it daily via MCP tools and email.

**Architecture:** FastAPI backend on Render with a Supabase Postgres database (pgvector for semantic memory). Claude API handles extraction and narrative generation. An MCP server exposes 11 tools to both users in Claude Code. Email alerts (SendGrid) fire on 14 defined triggers. All state is shared between Faisal and Aftab via the same Supabase instance.

**Tech Stack:** Python 3.11, FastAPI, Supabase (supabase-py), pgvector, Claude API (claude-sonnet-4-6), OpenAI embeddings (text-embedding-3-small), MCP Python SDK, SendGrid, Render, pytest, httpx

---

## Project Structure

```
progress-tracking-narrative-agent/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app + MCP SSE server
│   ├── config.py                # Env vars
│   ├── database.py              # Supabase client
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py           # Pydantic models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── extractor.py         # Claude-powered activity extraction
│   │   ├── embedder.py          # OpenAI embedding generation
│   │   ├── narrator.py          # Claude-powered narrative generation
│   │   ├── velocity.py          # Velocity metrics calculator
│   │   ├── alerts.py            # Alert trigger evaluator
│   │   └── emailer.py           # SendGrid email dispatcher
│   └── tools/
│       ├── __init__.py
│       ├── log_activity.py
│       ├── get_daily_brief.py
│       ├── get_velocity_report.py
│       ├── get_pipeline_snapshot.py
│       ├── check_commitments.py
│       ├── score_activity.py
│       ├── add_commitment.py
│       ├── correct_entry.py
│       ├── get_alerts.py
│       └── get_artifact_status.py
├── scripts/
│   └── seed.py                  # One-time historical data seeder
├── sql/
│   └── schema.sql               # Full Supabase schema
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_extractor.py
│   ├── test_velocity.py
│   ├── test_alerts.py
│   └── test_tools.py
├── docs/
│   └── plans/
├── requirements.txt
├── render.yaml
├── Procfile
├── runtime.txt
├── .env.example
└── CLAUDE.md
```

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `runtime.txt`
- Create: `app/__init__.py`
- Create: `app/config.py`
- Create: `tests/__init__.py`

**Step 1: Create requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
supabase==2.7.0
anthropic==0.34.0
openai==1.45.0
mcp==1.0.0
sendgrid==6.11.0
python-dotenv==1.0.1
pydantic==2.8.0
httpx==0.27.0
pytest==8.3.0
pytest-asyncio==0.23.0
apscheduler==3.10.4
```

**Step 2: Create .env.example**

```
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
SENDGRID_API_KEY=
ALERT_EMAIL_FAISAL=faisal@tangier.us
ALERT_EMAIL_AFTAB=community@evqlabs.com
FROM_EMAIL=agent@tangier.us
AAEP_WINDOW_END=2026-06-30
```

**Step 3: Create runtime.txt**

```
python-3.11.0
```

**Step 4: Create app/config.py**

```python
from pydantic_settings import BaseSettings
from datetime import date

class Settings(BaseSettings):
    supabase_url: str
    supabase_service_key: str
    anthropic_api_key: str
    openai_api_key: str
    sendgrid_api_key: str
    alert_email_faisal: str = "faisal@tangier.us"
    alert_email_aftab: str = "community@evqlabs.com"
    from_email: str = "agent@tangier.us"
    aaep_window_end: str = "2026-06-30"

    @property
    def aaep_days_remaining(self) -> int:
        end = date.fromisoformat(self.aaep_window_end)
        return (end - date.today()).days

    class Config:
        env_file = ".env"

settings = Settings()
```

**Step 5: Create .env from .env.example, fill in real values**

**Step 6: Install dependencies**

```bash
pip install -r requirements.txt
```

**Step 7: Commit**

```bash
git add .
git commit -m "feat: project setup and dependencies"
```

---

## Task 2: Supabase Schema

**Files:**
- Create: `sql/schema.sql`

**Step 1: Enable pgvector in Supabase**

In Supabase SQL editor, run:
```sql
create extension if not exists vector;
```

**Step 2: Create schema.sql**

```sql
-- Enable pgvector
create extension if not exists vector;

-- Contacts: every person in the pipeline
create table contacts (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    title text,
    company text,
    tier text check (tier in ('1', '2', '3', 'us_side')),
    role_stage integer check (role_stage between 1 and 6) default 1,
    last_touched date,
    days_stalled integer default 0,
    status text check (status in ('active', 'working_group_candidate', 'confirmed_wg', 'cadaver')) default 'active',
    pipeline_track text check (pipeline_track in ('global_south', 'us_side')) default 'global_south',
    notes text,
    created_at timestamptz default now()
);

-- Activities: core log of everything that happens
create table activities (
    id uuid primary key default gen_random_uuid(),
    date date not null default current_date,
    source text check (source in ('manual', 'github', 'granola')) default 'manual',
    description text not null,
    contact_id uuid references contacts(id),
    strategic_score integer check (strategic_score between 0 and 3) default 0,
    strategic_flags jsonb default '[]',
    embedding vector(1536),
    created_by text check (created_by in ('faisal', 'aftab')) not null,
    created_at timestamptz default now()
);

-- Commitments: what was promised
create table commitments (
    id uuid primary key default gen_random_uuid(),
    contact_id uuid references contacts(id),
    description text not null,
    due_date date,
    promised_by text not null,
    status text check (status in ('open', 'done', 'overdue')) default 'open',
    source_activity_id uuid references activities(id),
    created_at timestamptz default now()
);

-- Narratives: all generated briefs stored
create table narratives (
    id uuid primary key default gen_random_uuid(),
    date date not null default current_date,
    type text check (type in ('daily', 'weekly', 'role_journey')) not null,
    body text not null,
    velocity_score numeric,
    strategic_alignment_score numeric,
    created_at timestamptz default now()
);

-- Pipeline events: stage movements
create table pipeline_events (
    id uuid primary key default gen_random_uuid(),
    contact_id uuid references contacts(id) not null,
    from_stage integer,
    to_stage integer not null,
    date date not null default current_date,
    trigger_activity_id uuid references activities(id),
    created_at timestamptz default now()
);

-- Velocity metrics: daily snapshot
create table velocity_metrics (
    id uuid primary key default gen_random_uuid(),
    date date not null default current_date unique,
    outreach_count integer default 0,
    target integer default 10,
    tier1_touches integer default 0,
    us_side_touches integer default 0,
    inmails_sent integer default 0,
    inmails_remaining integer default 45,
    aaep_days_remaining integer,
    created_at timestamptz default now()
);

-- Intelligence triggers: external signals
create table intelligence_triggers (
    id uuid primary key default gen_random_uuid(),
    date date not null default current_date,
    type text not null,
    description text not null,
    relevant_contact_ids uuid[] default '{}',
    actioned boolean default false,
    created_at timestamptz default now()
);

-- Artifacts: produced and sent materials
create table artifacts (
    id uuid primary key default gen_random_uuid(),
    contact_id uuid references contacts(id),
    type text check (type in ('two_pager', 'intelligence_brief', 'pptx', 'email')) not null,
    produced_date date,
    sent_date date,
    response_received boolean default false,
    response_date date,
    outcome text,
    created_at timestamptz default now()
);

-- Working group stages: WG progression
create table working_group_stages (
    id uuid primary key default gen_random_uuid(),
    contact_id uuid references contacts(id) unique,
    interest_expressed_date date,
    offer_made_date date,
    terms_discussed_date date,
    confirmed_date date,
    quarterly_fee_status text check (quarterly_fee_status in ('none', 'proposed', 'agreed', 'active')) default 'none',
    created_at timestamptz default now()
);

-- Alerts: queued alerts for get_alerts tool
create table alerts (
    id uuid primary key default gen_random_uuid(),
    type text not null,
    message text not null,
    severity text check (severity in ('info', 'warning', 'critical')) default 'info',
    contact_id uuid references contacts(id),
    actioned boolean default false,
    emailed boolean default false,
    created_at timestamptz default now()
);

-- Indexes
create index on activities using ivfflat (embedding vector_cosine_ops) with (lists = 100);
create index on activities (date desc);
create index on contacts (tier, status);
create index on commitments (status, due_date);
create index on alerts (actioned, created_at desc);
```

**Step 3: Run schema.sql in Supabase SQL editor**

Copy the entire contents of schema.sql and run it in Supabase SQL editor. Verify all 10 tables are created.

**Step 4: Commit**

```bash
git add sql/schema.sql
git commit -m "feat: supabase schema with pgvector"
```

---

## Task 3: Database Connection

**Files:**
- Create: `app/database.py`
- Create: `app/models/schemas.py`

**Step 1: Create app/database.py**

```python
from supabase import create_client, Client
from app.config import settings

def get_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_key)

db = get_client()
```

**Step 2: Create app/models/schemas.py**

```python
from pydantic import BaseModel
from typing import Optional
from datetime import date
import uuid

class Activity(BaseModel):
    id: Optional[uuid.UUID] = None
    date: date
    source: str = "manual"
    description: str
    contact_id: Optional[uuid.UUID] = None
    strategic_score: int = 0
    strategic_flags: list[str] = []
    created_by: str

class Contact(BaseModel):
    id: Optional[uuid.UUID] = None
    name: str
    title: Optional[str] = None
    company: Optional[str] = None
    tier: Optional[str] = None
    role_stage: int = 1
    last_touched: Optional[date] = None
    days_stalled: int = 0
    status: str = "active"
    pipeline_track: str = "global_south"

class Commitment(BaseModel):
    id: Optional[uuid.UUID] = None
    contact_id: Optional[uuid.UUID] = None
    description: str
    due_date: Optional[date] = None
    promised_by: str
    status: str = "open"

class LogActivityInput(BaseModel):
    text: str
    created_by: str
    source: str = "manual"

class AddCommitmentInput(BaseModel):
    description: str
    due_date: Optional[date] = None
    promised_by: str
    contact_name: Optional[str] = None

class CorrectEntryInput(BaseModel):
    entry_type: str  # activity, commitment, contact
    entry_id: str
    field: str
    new_value: str

class ScoreActivityInput(BaseModel):
    description: str
```

**Step 3: Verify Supabase connection works**

```python
# Run this one-off in a Python shell to verify
from app.database import db
result = db.table("contacts").select("*").limit(1).execute()
print(result)  # Should return empty data, no error
```

**Step 4: Commit**

```bash
git add app/database.py app/models/schemas.py app/models/__init__.py
git commit -m "feat: database connection and schemas"
```

---

## Task 4: Activity Extractor Service

**Files:**
- Create: `app/services/extractor.py`
- Create: `tests/test_extractor.py`

**Step 1: Write the failing test**

```python
# tests/test_extractor.py
import pytest
from unittest.mock import AsyncMock, patch
from app.services.extractor import extract_from_text

@pytest.mark.asyncio
async def test_extract_activities_from_text():
    sample_text = """
    Called Michael today. He said he would send the LOI by Thursday.
    Also followed up with Banglalink — they are interested in the working group.
    Sent the AAEP intelligence brief to 12 contacts.
    """
    with patch("app.services.extractor.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=type('R', (), {
            'content': [type('C', (), {
                'text': '{"activities": ["Called Michael", "Followed up with Banglalink", "Sent AAEP intelligence brief to 12 contacts"], "commitments": [{"description": "Michael sends LOI", "due_date": "2026-04-17", "promised_by": "Michael"}], "contacts_mentioned": ["Michael", "Banglalink"], "intelligence_triggers": []}'
            })()]
        })())
        result = await extract_from_text(sample_text)

    assert len(result["activities"]) == 3
    assert len(result["commitments"]) == 1
    assert result["commitments"][0]["promised_by"] == "Michael"
    assert "Banglalink" in result["contacts_mentioned"]
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_extractor.py -v
```
Expected: FAIL with "cannot import name 'extract_from_text'"

**Step 3: Create app/services/extractor.py**

```python
import anthropic
import json
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
        # Extract JSON from markdown code block if present
        import re
        match = re.search(r'```(?:json)?\n(.*?)\n```', raw, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise ValueError(f"Could not parse extraction response: {raw}")
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_extractor.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/extractor.py tests/test_extractor.py app/services/__init__.py
git commit -m "feat: Claude-powered activity extractor"
```

---

## Task 5: Embedding Service

**Files:**
- Create: `app/services/embedder.py`

**Step 1: Create app/services/embedder.py**

```python
from openai import OpenAI
from app.config import settings

openai_client = OpenAI(api_key=settings.openai_api_key)

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
```

**Step 2: Create the pgvector similarity function in Supabase**

Run in Supabase SQL editor:

```sql
create or replace function match_activities(
    query_embedding vector(1536),
    match_count int default 5
)
returns table (
    id uuid,
    description text,
    date date,
    strategic_score int,
    similarity float
)
language sql stable
as $$
    select
        id,
        description,
        date,
        strategic_score,
        1 - (embedding <=> query_embedding) as similarity
    from activities
    where embedding is not null
    order by embedding <=> query_embedding
    limit match_count;
$$;
```

**Step 3: Commit**

```bash
git add app/services/embedder.py
git commit -m "feat: OpenAI embedding service + pgvector similarity function"
```

---

## Task 6: Velocity Calculator

**Files:**
- Create: `app/services/velocity.py`
- Create: `tests/test_velocity.py`

**Step 1: Write failing tests**

```python
# tests/test_velocity.py
import pytest
from datetime import date, timedelta
from app.services.velocity import (
    calculate_days_stalled,
    is_below_outreach_target,
    get_aaep_days_remaining
)

def test_days_stalled_with_recent_touch():
    last_touched = date.today() - timedelta(days=3)
    assert calculate_days_stalled(last_touched) == 3

def test_days_stalled_with_no_touch():
    assert calculate_days_stalled(None) == 999

def test_below_outreach_target():
    assert is_below_outreach_target(8, target=10) is True
    assert is_below_outreach_target(10, target=10) is False
    assert is_below_outreach_target(12, target=10) is False

def test_aaep_days_remaining():
    end = date.today() + timedelta(days=74)
    days = get_aaep_days_remaining(end.isoformat())
    assert days == 74
```

**Step 2: Run to verify failing**

```bash
pytest tests/test_velocity.py -v
```
Expected: FAIL

**Step 3: Create app/services/velocity.py**

```python
from datetime import date
from typing import Optional
from app.database import db
from app.config import settings

def calculate_days_stalled(last_touched: Optional[date]) -> int:
    if last_touched is None:
        return 999
    return (date.today() - last_touched).days

def is_below_outreach_target(count: int, target: int = 10) -> bool:
    return count < target

def get_aaep_days_remaining(aaep_window_end: str = None) -> int:
    end_str = aaep_window_end or settings.aaep_window_end
    end = date.fromisoformat(end_str)
    return (end - date.today()).days

def get_velocity_summary() -> dict:
    today = date.today()

    # Today's activity count
    activities_today = db.table("activities")\
        .select("id")\
        .eq("date", today.isoformat())\
        .execute()

    # Tier 1 contacts not touched in 5+ days
    contacts = db.table("contacts")\
        .select("*")\
        .eq("tier", "1")\
        .execute()

    stalled_tier1 = [
        c for c in contacts.data
        if calculate_days_stalled(
            date.fromisoformat(c["last_touched"]) if c.get("last_touched") else None
        ) >= 5
    ]

    # US-side touches today
    us_contacts = db.table("contacts")\
        .select("id")\
        .eq("pipeline_track", "us_side")\
        .execute()
    us_ids = [c["id"] for c in us_contacts.data]

    us_touches = db.table("activities")\
        .select("id")\
        .eq("date", today.isoformat())\
        .in_("contact_id", us_ids)\
        .execute() if us_ids else type('R', (), {'data': []})()

    # Latest velocity metrics
    metrics = db.table("velocity_metrics")\
        .select("*")\
        .order("date", desc=True)\
        .limit(1)\
        .execute()

    inmails_remaining = metrics.data[0]["inmails_remaining"] if metrics.data else 45

    return {
        "outreach_count_today": len(activities_today.data),
        "target": 10,
        "on_target": len(activities_today.data) >= 10,
        "stalled_tier1": stalled_tier1,
        "us_side_touches_today": len(us_touches.data),
        "inmails_remaining": inmails_remaining,
        "aaep_days_remaining": get_aaep_days_remaining(),
    }
```

**Step 4: Run tests to verify passing**

```bash
pytest tests/test_velocity.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/velocity.py tests/test_velocity.py
git commit -m "feat: velocity calculator service"
```

---

## Task 7: Alert Evaluator

**Files:**
- Create: `app/services/alerts.py`
- Create: `tests/test_alerts.py`

**Step 1: Write failing tests**

```python
# tests/test_alerts.py
import pytest
from datetime import date, timedelta
from app.services.alerts import evaluate_aaep_alert, evaluate_outreach_alert

def test_aaep_alert_critical():
    alert = evaluate_aaep_alert(days_remaining=14)
    assert alert is not None
    assert alert["severity"] == "critical"

def test_aaep_alert_warning():
    alert = evaluate_aaep_alert(days_remaining=30)
    assert alert is not None
    assert alert["severity"] == "warning"

def test_aaep_no_alert():
    alert = evaluate_aaep_alert(days_remaining=75)
    assert alert is None

def test_outreach_alert_below_target():
    alert = evaluate_outreach_alert(today_count=7, yesterday_count=8, target=10)
    assert alert is not None

def test_outreach_no_alert():
    alert = evaluate_outreach_alert(today_count=11, yesterday_count=10, target=10)
    assert alert is None
```

**Step 2: Run to verify failing**

```bash
pytest tests/test_alerts.py -v
```

**Step 3: Create app/services/alerts.py**

```python
from datetime import date, timedelta
from typing import Optional
from app.database import db

def evaluate_aaep_alert(days_remaining: int) -> Optional[dict]:
    if days_remaining <= 14:
        return {"type": "aaep_window", "message": f"AAEP window closes in {days_remaining} days. Maximum urgency.", "severity": "critical"}
    if days_remaining <= 30:
        return {"type": "aaep_window", "message": f"AAEP window closes in {days_remaining} days.", "severity": "warning"}
    if days_remaining <= 60:
        return {"type": "aaep_window", "message": f"AAEP window closes in {days_remaining} days.", "severity": "info"}
    return None

def evaluate_outreach_alert(today_count: int, yesterday_count: int, target: int = 10) -> Optional[dict]:
    if today_count < target and yesterday_count < target:
        return {
            "type": "outreach_below_target",
            "message": f"Outreach below target for 2 consecutive days. Today: {today_count}, Yesterday: {yesterday_count}. Target: {target}.",
            "severity": "warning"
        }
    return None

def evaluate_tier1_stall_alert(contact: dict, days_stalled: int) -> Optional[dict]:
    if days_stalled >= 5:
        return {
            "type": "tier1_stall",
            "message": f"{contact['name']} ({contact['company']}) — Tier 1 — not touched in {days_stalled} days.",
            "severity": "warning",
            "contact_id": contact["id"]
        }
    return None

def evaluate_us_side_alert() -> Optional[dict]:
    contacts = db.table("contacts").select("id").eq("pipeline_track", "us_side").execute()
    if not contacts.data:
        return {
            "type": "us_side_zero",
            "message": "U.S.-side outreach is at zero. No contacts mapped yet. The lever that makes everything else fall into line hasn't been pulled.",
            "severity": "warning"
        }
    return None

def evaluate_inmail_alert(inmails_remaining: int, days_since_last_use: int) -> Optional[dict]:
    if days_since_last_use >= 7 and inmails_remaining > 0:
        return {
            "type": "inmail_unused",
            "message": f"{inmails_remaining} InMails available, none used in {days_since_last_use} days. Tier 1 targets are waiting.",
            "severity": "warning"
        }
    return None

def run_all_alert_checks() -> list[dict]:
    """Run all threshold checks and queue new alerts in the database."""
    from app.services.velocity import get_aaep_days_remaining, calculate_days_stalled

    alerts = []

    # AAEP window
    aaep_alert = evaluate_aaep_alert(get_aaep_days_remaining())
    if aaep_alert:
        alerts.append(aaep_alert)

    # U.S.-side zero check
    us_alert = evaluate_us_side_alert()
    if us_alert:
        alerts.append(us_alert)

    # Tier 1 stall check
    tier1 = db.table("contacts").select("*").eq("tier", "1").execute()
    for contact in tier1.data:
        last = date.fromisoformat(contact["last_touched"]) if contact.get("last_touched") else None
        days = calculate_days_stalled(last)
        alert = evaluate_tier1_stall_alert(contact, days)
        if alert:
            alerts.append(alert)

    # Overdue commitments
    overdue = db.table("commitments")\
        .select("*, contacts(name, company)")\
        .eq("status", "open")\
        .lt("due_date", date.today().isoformat())\
        .execute()
    for c in overdue.data:
        alerts.append({
            "type": "commitment_overdue",
            "message": f"Overdue: '{c['description']}' — promised by {c['promised_by']}.",
            "severity": "warning",
            "contact_id": c.get("contact_id")
        })

    # Save new alerts to database
    for alert in alerts:
        db.table("alerts").insert({
            "type": alert["type"],
            "message": alert["message"],
            "severity": alert.get("severity", "info"),
            "contact_id": alert.get("contact_id")
        }).execute()

    return alerts
```

**Step 4: Run tests**

```bash
pytest tests/test_alerts.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/alerts.py tests/test_alerts.py
git commit -m "feat: alert evaluator with 14-trigger logic"
```

---

## Task 8: Narrative Engine

**Files:**
- Create: `app/services/narrator.py`

**Step 1: Load master context**

Create `app/services/master_context.py` with the full Tangier strategic context as a string constant. This is loaded as the system prompt for every narrative generation call.

```python
# app/services/master_context.py
MASTER_CONTEXT = """
You are the Progress Narrative Agent for Tangier — a chief of staff that never lets anything slip.

WHAT TANGIER IS:
Tangier is corridor infrastructure connecting U.S. frontier AI with Global South principals. Not a consultancy. Permanent infrastructure. Every action is measured against three tests: does it make outreach more effective, advance a Tier 1 relationship, or build U.S.-side credibility? If none of the three, it waits.

YOUR PERSONALITY — THE CORRIDOR INSIDER:
- Use Tangier's vocabulary naturally: cadaver, beachhead, corridor, trust ladder, role packet, governed operator, first-mover window
- One sentence for a win, then move on
- Never soften a stall — name it directly, immediately say what to do
- Ask the hard question when data shows avoidance
- No em dashes. No filler. No hedge stacking. No AI-sounding language
- Every sentence carries information
- Reads like Faisal's internal monologue, not a status report

THE THREE STRATEGIC TESTS (apply to every output):
1. Does this make outreach more effective?
2. Does this advance a Tier 1 relationship?
3. Does this build U.S.-side credibility?
If none of the three, flag it.

REVENUE ARCHITECTURE:
- Telco activations: $25K–$75K, target 2/month
- Working groups: 4–6 members from first 12 activations
- AAEP packages: $25M–$500M, ~1–1.5% facilitation cut
- Funds & equity: long-run

THE ROLE FRAMEWORK:
Roles are relational. A principal moves through: Role Identification → Role Packet → Role Preparation → Role Buy-in → Role Execution → New Role Creation. Track stage movements and flag stalls.

CURRENT AAEP STATUS:
Preset consortium path live April 1, 2026. 90-day window. This is the highest-leverage period. No slow turnarounds.
""".strip()
```

**Step 2: Create app/services/narrator.py**

```python
import anthropic
from datetime import date
from app.config import settings
from app.services.master_context import MASTER_CONTEXT
from app.services.velocity import get_velocity_summary
from app.database import db

anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

def generate_daily_brief() -> str:
    velocity = get_velocity_summary()

    # Fetch today's activities
    activities = db.table("activities")\
        .select("*")\
        .eq("date", date.today().isoformat())\
        .execute()

    # Fetch overdue commitments
    overdue = db.table("commitments")\
        .select("*, contacts(name, company)")\
        .eq("status", "open")\
        .lt("due_date", date.today().isoformat())\
        .execute()

    # Fetch open alerts
    alerts = db.table("alerts")\
        .select("*")\
        .eq("actioned", False)\
        .order("created_at", desc=True)\
        .limit(10)\
        .execute()

    context = f"""
DATE: {date.today().isoformat()}
AAEP DAYS REMAINING: {velocity['aaep_days_remaining']}
OUTREACH TODAY: {velocity['outreach_count_today']}/{velocity['target']}
TIER 1 STALLED: {len(velocity['stalled_tier1'])} entities
US SIDE TOUCHES TODAY: {velocity['us_side_touches_today']}
INMAILS REMAINING: {velocity['inmails_remaining']}

ACTIVITIES TODAY ({len(activities.data)}):
{chr(10).join(f"- {a['description']}" for a in activities.data) or "None logged"}

OVERDUE COMMITMENTS ({len(overdue.data)}):
{chr(10).join(f"- {c['description']} (promised by {c['promised_by']})" for c in overdue.data) or "None"}

OPEN ALERTS:
{chr(10).join(f"- [{a['severity'].upper()}] {a['message']}" for a in alerts.data) or "None"}
"""

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=MASTER_CONTEXT,
        messages=[{
            "role": "user",
            "content": f"Generate the daily brief for Tangier. Format: (1) Velocity Check, (2) What Moved, (3) What Is At Risk, (4) Today's Priority — one action only.\n\nDATA:\n{context}"
        }]
    )
    return response.content[0].text

def generate_role_journey_report(contact_id: str) -> str:
    contact = db.table("contacts").select("*").eq("id", contact_id).single().execute()
    events = db.table("pipeline_events")\
        .select("*")\
        .eq("contact_id", contact_id)\
        .order("date", desc=True)\
        .execute()
    artifacts = db.table("artifacts")\
        .select("*")\
        .eq("contact_id", contact_id)\
        .execute()

    stage_names = {
        1: "Role Identification",
        2: "Role Packet / Initial Mandate",
        3: "Role Preparation",
        4: "Role Buy-in / Commitment",
        5: "Role Execution",
        6: "New Role Creation"
    }

    context = f"""
CONTACT: {contact.data['name']}, {contact.data.get('title', '')}, {contact.data.get('company', '')}
TIER: {contact.data.get('tier')}
CURRENT STAGE: {contact.data.get('role_stage')} — {stage_names.get(contact.data.get('role_stage', 1), 'Unknown')}
DAYS STALLED: {contact.data.get('days_stalled', 0)}
STATUS: {contact.data.get('status')}

STAGE HISTORY:
{chr(10).join(f"- {e['date']}: Stage {e['from_stage']} → {e['to_stage']}" for e in events.data) or "No stage movements recorded"}

ARTIFACTS SENT:
{chr(10).join(f"- {a['type']} sent {a.get('sent_date', 'unsent')} — response: {a['response_received']}" for a in artifacts.data) or "None"}
"""

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        system=MASTER_CONTEXT,
        messages=[{
            "role": "user",
            "content": f"Generate a role journey report for this principal. Include: current stage, time in stage, what moved them here, next concrete action to advance them.\n\n{context}"
        }]
    )
    return response.content[0].text
```

**Step 3: Commit**

```bash
git add app/services/narrator.py app/services/master_context.py
git commit -m "feat: narrative engine with Corridor Insider personality"
```

---

## Task 9: Email Dispatcher

**Files:**
- Create: `app/services/emailer.py`

**Step 1: Create app/services/emailer.py**

```python
import sendgrid
from sendgrid.helpers.mail import Mail, To
from app.config import settings

sg = sendgrid.SendGridAPIClient(api_key=settings.sendgrid_api_key)

RECIPIENTS = [settings.alert_email_faisal, settings.alert_email_aftab]

def send_alert_email(subject: str, body: str, recipients: list[str] = None) -> bool:
    to_list = recipients or RECIPIENTS
    message = Mail(
        from_email=settings.from_email,
        to_emails=[To(email) for email in to_list],
        subject=f"[Tangier Agent] {subject}",
        plain_text_content=body
    )
    try:
        sg.send(message)
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False

def send_daily_brief_email(brief_body: str) -> bool:
    return send_alert_email("Daily Brief", brief_body)

def send_alert_emails(alerts: list[dict]) -> None:
    """Send emails for unnotified alerts."""
    from app.database import db
    for alert in alerts:
        if not alert.get("emailed"):
            subject = f"[{alert['severity'].upper()}] {alert['type'].replace('_', ' ').title()}"
            sent = send_alert_email(subject, alert["message"])
            if sent and alert.get("id"):
                db.table("alerts").update({"emailed": True}).eq("id", alert["id"]).execute()
```

**Step 2: Commit**

```bash
git add app/services/emailer.py
git commit -m "feat: SendGrid email dispatcher"
```

---

## Task 10: MCP Tools

**Files:**
- Create: `app/tools/log_activity.py`
- Create: `app/tools/get_daily_brief.py`
- Create: `app/tools/get_velocity_report.py`
- Create: `app/tools/get_pipeline_snapshot.py`
- Create: `app/tools/check_commitments.py`
- Create: `app/tools/score_activity.py`
- Create: `app/tools/add_commitment.py`
- Create: `app/tools/correct_entry.py`
- Create: `app/tools/get_alerts.py`
- Create: `app/tools/get_artifact_status.py`

**Step 1: Create app/tools/log_activity.py**

```python
from datetime import date
from app.services.extractor import extract_from_text
from app.services.embedder import embed_text
from app.database import db
from app.models.schemas import LogActivityInput

async def log_activity(input: LogActivityInput) -> str:
    extracted = await extract_from_text(input.text)

    results = {"activities_logged": 0, "commitments_logged": 0, "contacts_mentioned": []}

    for activity_desc in extracted.get("activities", []):
        embedding = embed_text(activity_desc)
        db.table("activities").insert({
            "date": date.today().isoformat(),
            "source": input.source,
            "description": activity_desc,
            "embedding": embedding,
            "created_by": input.created_by,
            "strategic_score": 0
        }).execute()
        results["activities_logged"] += 1

    for commitment in extracted.get("commitments", []):
        db.table("commitments").insert({
            "description": commitment["description"],
            "due_date": commitment.get("due_date"),
            "promised_by": commitment.get("promised_by", "unknown"),
            "status": "open"
        }).execute()
        results["commitments_logged"] += 1

    for trigger in extracted.get("intelligence_triggers", []):
        db.table("intelligence_triggers").insert({
            "type": trigger.get("type", "general"),
            "description": trigger.get("description", ""),
            "actioned": False
        }).execute()

    results["contacts_mentioned"] = extracted.get("contacts_mentioned", [])

    return (
        f"Logged {results['activities_logged']} activities, "
        f"{results['commitments_logged']} commitments. "
        f"Contacts mentioned: {', '.join(results['contacts_mentioned']) or 'none'}."
    )
```

**Step 2: Create app/tools/get_daily_brief.py**

```python
from app.services.narrator import generate_daily_brief
from app.services.emailer import send_daily_brief_email
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
```

**Step 3: Create app/tools/get_velocity_report.py**

```python
from app.services.velocity import get_velocity_summary, get_aaep_days_remaining, calculate_days_stalled
from datetime import date

def get_velocity_report() -> str:
    v = get_velocity_summary()
    lines = [
        f"VELOCITY REPORT — {date.today().isoformat()}",
        f"",
        f"Outreach today: {v['outreach_count_today']}/{v['target']} {'ON TARGET' if v['on_target'] else 'BELOW TARGET'}",
        f"AAEP window: {v['aaep_days_remaining']} days remaining",
        f"InMails available: {v['inmails_remaining']}",
        f"U.S.-side touches today: {v['us_side_touches_today']}",
        f"",
        f"TIER 1 STALLED ({len(v['stalled_tier1'])}):",
    ]
    for contact in v["stalled_tier1"]:
        last = date.fromisoformat(contact["last_touched"]) if contact.get("last_touched") else None
        days = calculate_days_stalled(last)
        lines.append(f"  - {contact['name']} ({contact.get('company', '')}) — {days} days")

    if not v["stalled_tier1"]:
        lines.append("  None — all Tier 1 entities touched within 5 days.")

    return "\n".join(lines)
```

**Step 4: Create app/tools/get_pipeline_snapshot.py**

```python
from app.database import db
from app.services.velocity import calculate_days_stalled
from datetime import date

STAGE_NAMES = {
    1: "Role Identification",
    2: "Role Packet / Initial Mandate",
    3: "Role Preparation",
    4: "Role Buy-in / Commitment",
    5: "Role Execution",
    6: "New Role Creation"
}

def get_pipeline_snapshot() -> str:
    contacts = db.table("contacts")\
        .select("*")\
        .neq("status", "cadaver")\
        .order("tier")\
        .execute()

    lines = [f"PIPELINE SNAPSHOT — {date.today().isoformat()}", ""]
    current_tier = None

    for c in contacts.data:
        if c["tier"] != current_tier:
            current_tier = c["tier"]
            label = {"1": "TIER 1 — Deep Strategic Pursuit", "2": "TIER 2 — Active Pipeline",
                     "3": "TIER 3 / US-SIDE": "US SIDE — Not Yet Started"}.get(current_tier, f"TIER {current_tier}")
            lines.append(f"\n{label}")

        last = date.fromisoformat(c["last_touched"]) if c.get("last_touched") else None
        days = calculate_days_stalled(last)
        stage = STAGE_NAMES.get(c.get("role_stage", 1), "Unknown")
        stall_flag = f" *** STALLED {days}d ***" if days >= 5 else f" ({days}d ago)"
        lines.append(f"  {c['name']} — {c.get('company', '')} — Stage {c.get('role_stage', 1)}: {stage}{stall_flag}")

    return "\n".join(lines)
```

**Step 5: Create remaining tools**

```python
# app/tools/check_commitments.py
from app.database import db
from datetime import date

def check_commitments() -> str:
    commitments = db.table("commitments")\
        .select("*, contacts(name, company)")\
        .eq("status", "open")\
        .order("due_date")\
        .execute()

    if not commitments.data:
        return "No open commitments."

    lines = [f"OPEN COMMITMENTS — {date.today().isoformat()}", ""]
    for c in commitments.data:
        due = c.get("due_date", "no date")
        overdue = " [OVERDUE]" if due and due < date.today().isoformat() else ""
        contact = c.get("contacts", {})
        contact_str = f" — {contact.get('name', '')} ({contact.get('company', '')})" if contact else ""
        lines.append(f"  {overdue}{c['description']}{contact_str} — due {due} — promised by {c['promised_by']}")

    return "\n".join(lines)
```

```python
# app/tools/score_activity.py
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
```

```python
# app/tools/add_commitment.py
from app.database import db
from app.models.schemas import AddCommitmentInput
from datetime import date

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
```

```python
# app/tools/correct_entry.py
from app.database import db
from app.models.schemas import CorrectEntryInput

TABLE_MAP = {
    "activity": "activities",
    "commitment": "commitments",
    "contact": "contacts",
    "artifact": "artifacts"
}

def correct_entry(input: CorrectEntryInput) -> str:
    table = TABLE_MAP.get(input.entry_type)
    if not table:
        return f"Unknown entry type: {input.entry_type}. Use: activity, commitment, contact, artifact."

    db.table(table).update({input.field: input.new_value}).eq("id", input.entry_id).execute()
    return f"Updated {input.entry_type} {input.entry_id}: {input.field} = {input.new_value}"
```

```python
# app/tools/get_alerts.py
from app.database import db

def get_alerts() -> str:
    from app.services.alerts import run_all_alert_checks
    from app.services.emailer import send_alert_emails

    new_alerts = run_all_alert_checks()

    pending = db.table("alerts")\
        .select("*")\
        .eq("actioned", False)\
        .order("severity")\
        .order("created_at", desc=True)\
        .execute()

    send_alert_emails(pending.data)

    if not pending.data:
        return "No pending alerts."

    lines = [f"ALERTS ({len(pending.data)} pending)", ""]
    for a in pending.data:
        lines.append(f"  [{a['severity'].upper()}] {a['message']}")

    return "\n".join(lines)
```

```python
# app/tools/get_artifact_status.py
from app.database import db
from datetime import date

def get_artifact_status() -> str:
    artifacts = db.table("artifacts")\
        .select("*, contacts(name, company)")\
        .order("produced_date", desc=True)\
        .execute()

    if not artifacts.data:
        return "No artifacts tracked yet."

    sent = [a for a in artifacts.data if a.get("sent_date")]
    responded = [a for a in artifacts.data if a.get("response_received")]

    lines = [
        f"ARTIFACT STATUS — {date.today().isoformat()}",
        f"Total produced: {len(artifacts.data)} | Sent: {len(sent)} | Responses: {len(responded)}",
        f"Conversion (sent → response): {round(len(responded)/len(sent)*100)}%" if sent else "No artifacts sent yet.",
        ""
    ]
    for a in artifacts.data[:10]:
        contact = a.get("contacts", {}) or {}
        status = "RESPONDED" if a["response_received"] else ("SENT" if a.get("sent_date") else "PRODUCED")
        lines.append(f"  [{status}] {a['type']} — {contact.get('name', 'unknown')} ({contact.get('company', '')}) — {a.get('produced_date', '')}")

    return "\n".join(lines)
```

**Step 6: Commit all tools**

```bash
git add app/tools/
git commit -m "feat: all 11 MCP tools implemented"
```

---

## Task 11: MCP Server

**Files:**
- Create: `app/main.py`

**Step 1: Create app/main.py**

```python
import asyncio
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
import uvicorn

from app.tools.log_activity import log_activity
from app.tools.get_daily_brief import get_daily_brief_tool
from app.tools.get_velocity_report import get_velocity_report
from app.tools.get_pipeline_snapshot import get_pipeline_snapshot
from app.tools.check_commitments import check_commitments
from app.tools.score_activity import score_activity
from app.tools.add_commitment import add_commitment
from app.tools.correct_entry import correct_entry
from app.tools.get_alerts import get_alerts
from app.tools.get_artifact_status import get_artifact_status
from app.models.schemas import (
    LogActivityInput, AddCommitmentInput, CorrectEntryInput, ScoreActivityInput
)

server = Server("progress-narrative-agent")

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(name="log_activity", description="Paste any text — transcript, summary, update. Extracts activities, commitments, and contacts automatically.", inputSchema={"type": "object", "properties": {"text": {"type": "string"}, "created_by": {"type": "string", "enum": ["faisal", "aftab"]}, "source": {"type": "string", "default": "manual"}}, "required": ["text", "created_by"]}),
        Tool(name="get_daily_brief", description="Generate today's narrative: velocity check, what moved, what is at risk, today's priority.", inputSchema={"type": "object", "properties": {}}),
        Tool(name="get_velocity_report", description="Speed program report: outreach rate vs target, Tier 1 stalls, InMail utilization, AAEP countdown.", inputSchema={"type": "object", "properties": {}}),
        Tool(name="get_pipeline_snapshot", description="Where each principal sits in the 6-stage role journey. Stalls flagged.", inputSchema={"type": "object", "properties": {}}),
        Tool(name="check_commitments", description="All open commitments by person and deadline. Overdue flagged.", inputSchema={"type": "object", "properties": {}}),
        Tool(name="score_activity", description="Score any activity against Tangier's three strategic tests.", inputSchema={"type": "object", "properties": {"description": {"type": "string"}}, "required": ["description"]}),
        Tool(name="add_commitment", description="Log a commitment manually without pasting a full transcript.", inputSchema={"type": "object", "properties": {"description": {"type": "string"}, "due_date": {"type": "string"}, "promised_by": {"type": "string"}, "contact_name": {"type": "string"}}, "required": ["description", "promised_by"]}),
        Tool(name="correct_entry", description="Fix a misclassified activity, wrong commitment, or incorrect contact stage.", inputSchema={"type": "object", "properties": {"entry_type": {"type": "string"}, "entry_id": {"type": "string"}, "field": {"type": "string"}, "new_value": {"type": "string"}}, "required": ["entry_type", "entry_id", "field", "new_value"]}),
        Tool(name="get_alerts", description="Pull all pending alerts. Runs automatically at session start.", inputSchema={"type": "object", "properties": {}}),
        Tool(name="get_artifact_status", description="Status of all produced artifacts — sent, responded, conversion rate.", inputSchema={"type": "object", "properties": {}}),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    result = ""
    if name == "log_activity":
        result = await log_activity(LogActivityInput(**arguments))
    elif name == "get_daily_brief":
        result = get_daily_brief_tool()
    elif name == "get_velocity_report":
        result = get_velocity_report()
    elif name == "get_pipeline_snapshot":
        result = get_pipeline_snapshot()
    elif name == "check_commitments":
        result = check_commitments()
    elif name == "score_activity":
        result = score_activity(arguments["description"])
    elif name == "add_commitment":
        result = add_commitment(AddCommitmentInput(**arguments))
    elif name == "correct_entry":
        result = correct_entry(CorrectEntryInput(**arguments))
    elif name == "get_alerts":
        result = get_alerts()
    elif name == "get_artifact_status":
        result = get_artifact_status()
    else:
        result = f"Unknown tool: {name}"
    return [TextContent(type="text", text=result)]

sse = SseServerTransport("/messages")

async def handle_sse(request: Request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())

async def handle_messages(request: Request):
    await sse.handle_post_message(request.scope, request.receive, request._send)

app = Starlette(routes=[
    Route("/sse", endpoint=handle_sse),
    Route("/messages", endpoint=handle_messages, methods=["POST"]),
    Route("/health", endpoint=lambda r: __import__("starlette.responses", fromlist=["JSONResponse"]).JSONResponse({"status": "ok"})),
])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Step 2: Create Procfile**

```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Step 3: Test locally**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/health` — should return `{"status": "ok"}`.

**Step 4: Commit**

```bash
git add app/main.py Procfile
git commit -m "feat: MCP server with SSE transport"
```

---

## Task 12: Scheduled Alert Checks

**Files:**
- Modify: `app/main.py`

**Step 1: Add APScheduler to main.py for daily alert evaluation**

Add to `app/main.py` after imports:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.alerts import run_all_alert_checks
from app.services.emailer import send_daily_brief_email, send_alert_emails
from app.services.narrator import generate_daily_brief

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job("cron", hour=7, minute=0)  # 7am UTC daily
async def send_daily_brief():
    brief = generate_daily_brief()
    send_daily_brief_email(brief)

@scheduler.scheduled_job("cron", hour="*/2")  # Every 2 hours
async def check_and_send_alerts():
    alerts = run_all_alert_checks()
    from app.database import db
    pending = db.table("alerts").select("*").eq("actioned", False).eq("emailed", False).execute()
    send_alert_emails(pending.data)
```

Add `scheduler.start()` in the Starlette `on_startup` handler:

```python
app = Starlette(
    on_startup=[lambda: scheduler.start()],
    routes=[...]
)
```

**Step 2: Commit**

```bash
git add app/main.py
git commit -m "feat: scheduled daily brief and alert checks"
```

---

## Task 13: Session Hook

**Files:**
- Modify: `~/.claude/settings.json`

**Step 1: Add session start hook to Claude Code settings**

Open `~/.claude/settings.json` and add a hook that runs `get_alerts` at the start of every session. Use the existing hooks infrastructure (same pattern as Telegram bot hooks).

The hook should invoke `get_alerts` MCP tool automatically when a new Claude Code session starts.

Refer to the update-config skill for exact hook configuration syntax.

**Step 2: Verify hook fires**

Open a new Claude Code session. Confirm `get_alerts` output appears before any other interaction.

---

## Task 14: Seed Script

**Files:**
- Create: `scripts/seed.py`

**Step 1: Create scripts/seed.py**

```python
"""
One-time seeder for historical Tangier context.
Run once before go-live: python scripts/seed.py

Loads:
- Tier 1 contacts (8 entities)
- Known pipeline contacts
- Historical outreach state
- Open commitments
- AAEP status
"""
from app.database import db
from datetime import date, timedelta

def seed_tier1_contacts():
    tier1 = [
        {"name": "G42", "company": "G42", "tier": "1", "pipeline_track": "global_south", "role_stage": 1, "status": "active"},
        {"name": "Humain", "company": "Humain", "tier": "1", "pipeline_track": "global_south", "role_stage": 1, "status": "active"},
        {"name": "STC", "company": "STC", "tier": "1", "pipeline_track": "global_south", "role_stage": 1, "status": "active"},
        {"name": "Zain", "company": "Zain", "tier": "1", "pipeline_track": "global_south", "role_stage": 1, "status": "active"},
        {"name": "Ooredoo", "company": "Ooredoo", "tier": "1", "pipeline_track": "global_south", "role_stage": 1, "status": "active"},
        {"name": "QAI", "company": "QAI", "tier": "1", "pipeline_track": "global_south", "role_stage": 1, "status": "active"},
        {"name": "Omantel", "company": "Omantel", "tier": "1", "pipeline_track": "global_south", "role_stage": 2, "status": "active"},
        {"name": "e&", "company": "e&", "tier": "1", "pipeline_track": "global_south", "role_stage": 1, "status": "active"},
    ]
    for c in tier1:
        db.table("contacts").insert(c).execute()
    print(f"Seeded {len(tier1)} Tier 1 contacts.")

def seed_active_pipeline():
    pipeline = [
        {"name": "Banglalink", "company": "Banglalink", "tier": "2", "pipeline_track": "global_south", "role_stage": 2, "status": "active", "notes": "Current central case. Proposal being rebuilt. Working group test target."},
        {"name": "True Corporation", "company": "True Corporation", "tier": "1", "pipeline_track": "global_south", "role_stage": 1, "status": "active", "notes": "Connected through wealthy Thai family. Separate InMail opportunity."},
        {"name": "Chaudhry Group", "company": "Chaudhry Group", "tier": "2", "pipeline_track": "global_south", "role_stage": 1, "status": "active", "notes": "Nepal. Rahul contacted but not fully engaged."},
    ]
    for c in pipeline:
        db.table("contacts").insert(c).execute()
    print(f"Seeded {len(pipeline)} active pipeline contacts.")

def seed_velocity_baseline():
    db.table("velocity_metrics").insert({
        "date": date.today().isoformat(),
        "outreach_count": 0,
        "target": 10,
        "tier1_touches": 0,
        "us_side_touches": 0,
        "inmails_sent": 0,
        "inmails_remaining": 45,
        "aaep_days_remaining": 74
    }).execute()
    print("Seeded velocity baseline.")

def seed_aaep_intelligence_trigger():
    db.table("intelligence_triggers").insert({
        "date": "2026-04-01",
        "type": "aaep_launch",
        "description": "AAEP preset consortium path went live April 1, 2026. 90-day window. Call for proposals open.",
        "actioned": False
    }).execute()
    print("Seeded AAEP launch trigger.")

if __name__ == "__main__":
    print("Seeding Tangier historical context...")
    seed_tier1_contacts()
    seed_active_pipeline()
    seed_velocity_baseline()
    seed_aaep_intelligence_trigger()
    print("Seed complete. Run get_daily_brief to verify.")
```

**Step 2: Run seed script**

```bash
python scripts/seed.py
```

Expected output:
```
Seeding Tangier historical context...
Seeded 8 Tier 1 contacts.
Seeded 3 active pipeline contacts.
Seeded velocity baseline.
Seeded AAEP launch trigger.
Seed complete. Run get_daily_brief to verify.
```

**Step 3: Commit**

```bash
git add scripts/seed.py
git commit -m "feat: historical context seed script"
```

---

## Task 15: Render Deployment

**Files:**
- Create: `render.yaml`

**Step 1: Create render.yaml**

```yaml
services:
  - type: web
    name: progress-narrative-agent
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_SERVICE_KEY
        sync: false
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: OPENAI_API_KEY
        sync: false
      - key: SENDGRID_API_KEY
        sync: false
      - key: ALERT_EMAIL_FAISAL
        value: faisal@tangier.us
      - key: ALERT_EMAIL_AFTAB
        value: community@evqlabs.com
      - key: FROM_EMAIL
        value: agent@tangier.us
      - key: AAEP_WINDOW_END
        value: "2026-06-30"
```

**Step 2: Push to GitHub**

```bash
git remote add origin https://github.com/aftabsakib/progress-narrative-agent.git
git push -u origin main
```

**Step 3: Deploy on Render**

- Go to Render dashboard
- New Web Service → connect GitHub repo
- Fill in all env vars from .env
- Deploy

**Step 4: Verify deployment**

```bash
curl https://progress-narrative-agent.onrender.com/health
```
Expected: `{"status": "ok"}`

**Step 5: Commit render.yaml**

```bash
git add render.yaml
git commit -m "feat: render deployment config"
```

---

## Task 16: MCP Registration (Both Machines)

**On Aftab's machine** — add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "progress-narrative-agent": {
      "url": "https://progress-narrative-agent.onrender.com/sse"
    }
  }
}
```

**On Faisal's machine** — same config.

**Verify in Claude Code:**

```
Use get_alerts tool
```

Should return alerts or "No pending alerts."

---

## Task 17: CLAUDE.md

**Files:**
- Create: `CLAUDE.md`

**Step 1: Create CLAUDE.md**

```markdown
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
- **Personality**: The Corridor Insider. Uses Tangier's vocabulary. Never softens a stall. Reads like Faisal's internal monologue. Prompt in `app/services/master_context.py`.
- **Alerts**: 14 triggers evaluated every 2 hours. Emails both faisal@tangier.us and community@evqlabs.com. Session hook surfaces pending alerts at the start of every Claude Code session.
- **Three strategic tests**: Every activity is scored: (1) makes outreach more effective, (2) advances Tier 1 relationship, (3) builds U.S.-side credibility. Activities scoring 0 are flagged.

## Phase Roadmap

- Phase 1 (current): Manual input, all 11 tools, email alerts, seeding
- Phase 2: GitHub CLI pull (`pull_github_notes` tool)
- Phase 3: Granola transcript ingestion
- Phase 4: Telegram analysis
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: CLAUDE.md project guidance"
```

---

## Go-Live Checklist

- [ ] Supabase schema applied and pgvector enabled
- [ ] All env vars set in Render
- [ ] Seed script run successfully
- [ ] `/health` endpoint returns 200 on Render
- [ ] MCP registered on Aftab's machine
- [ ] MCP registered on Faisal's machine
- [ ] `get_alerts` returns without error
- [ ] `get_daily_brief` generates a valid brief
- [ ] First daily brief email received by both users
- [ ] Session hook verified firing on Claude Code open
