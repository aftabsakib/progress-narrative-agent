# Progress Tracking and Narrative Agent — Design Document
*Approved: April 16, 2026*

---

## What This Is

An automated chief of staff for Tangier. It monitors all organizational activity, tracks the velocity of corridor construction, holds Faisal and Aftab accountable to commitments, and generates ongoing narrative about what is moving, what is stalling, and what needs attention next.

It does not replace judgment. It makes sure nothing slips through and that every action is tested against the right questions.

The three strategic tests that govern every output:
> Does this make outreach more effective, advance a Tier 1 relationship, or build U.S.-side credibility? If none of the three, it waits.

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│        MCP Interface (Claude Code terminal)           │
│              Faisal (Dubai) + Aftab (Lahore)          │
└───────────────────────┬──────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────┐
│              FastAPI Backend (Render)                  │
│                                                        │
│   Ingestion Layer → Memory Layer → Narrative Engine   │
│                          ↕                             │
│              Accountability Tracker                    │
│                          ↕                             │
│               Alert Dispatcher (Email)                 │
└───────────────────────┬──────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────┐
│                    Supabase                            │
│  activities │ contacts │ commitments │ narratives      │
│  pipeline_events │ velocity_metrics │ intelligence_    │
│  triggers │ artifacts │ working_group_stages           │
│  + pgvector (semantic memory on activities)            │
└──────────────────────────────────────────────────────┘
```

**Phase plan:**
- Phase 1 (24–48 hrs): MCP server live, manual input, narrative engine, commitment tracking, email alerts, seeding of historical context
- Phase 2: GitHub CLI pull integration
- Phase 3: Granola transcript ingestion
- Phase 4: Telegram message analysis

---

## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Backend | Python + FastAPI | Consistent with EMA and Outreach Machine |
| Storage | Supabase + pgvector | Structured data + semantic memory on activities |
| Inference | Claude API (Sonnet) with prompt caching | Narrative generation; caching keeps master context warm cheaply |
| Interface | MCP server | Both users in Claude Code terminal |
| Alerts | Email via SMTP/SendGrid | Works across time zones; both users regardless of session state |
| Deploy | Render | Already deployed there |

pgvector enables semantic retrieval — when generating a narrative, the agent pulls situations similar to the current one from history. This is what makes it feel like an accumulating intelligence rather than a log.

---

## MCP Tools

| Tool | What it does |
|---|---|
| `log_activity` | Paste any input — transcript, summary, update, Granola export. Agent extracts activities, commitments, contacts touched, and role stage movements. Tags `created_by: faisal` or `created_by: aftab`. |
| `get_daily_brief` | Morning narrative: velocity check, what moved, what is at risk, today's single highest-leverage action. |
| `get_velocity_report` | The speed program. Outreach rate vs. 9–10/day target, pipeline advancement rate per contact, days-since-last-touch per Tier 1 entity, InMail utilization, U.S.-side outreach status, AAEP days remaining. |
| `get_pipeline_snapshot` | Where each principal sits in the 6-stage role journey. Flags who is stalled and for how long. |
| `check_commitments` | All open commitments by person and deadline. Flags overdue. |
| `score_activity` | Evaluates any described activity against the three strategic tests. Returns a score and explains why. |
| `add_commitment` | Manually log a commitment or follow-up without pasting a full transcript. |
| `correct_entry` | Fix a misclassified activity, wrong commitment attribution, or incorrect contact stage. Keeps the memory layer clean without going into the database directly. |
| `get_alerts` | Pull all pending alerts surfaced since last session. Runs automatically via session hook at the start of every Claude Code session. |
| `get_artifact_status` | Status of all produced artifacts — which two-pagers and intelligence briefs went to whom, response received or not, artifact-to-call conversion rate. |
| `pull_github_notes` | Phase 2 — pulls meeting notes from GitHub repos and runs the same ingestion pipeline. |

---

## Data Model

**`activities`**
Every input broken into individual logged activities.
```
id, date, source (manual/github/granola), description,
contact_id, strategic_score (0–3 tests passed),
embedding (vector), created_by (faisal/aftab)
```

**`contacts`**
Every person in the pipeline.
```
id, name, title, company, tier (1/2/3/us_side),
role_stage (1–6), last_touched, days_stalled,
status (active/working_group_candidate/confirmed_wg/cadaver),
pipeline_track (global_south/us_side)
```

**`commitments`**
What was promised by whom and when.
```
id, contact_id, description, due_date,
promised_by, status (open/done/overdue),
source_activity_id
```

**`narratives`**
All generated briefs stored for continuity and pattern analysis.
```
id, date, type (daily/weekly/role_journey),
body, velocity_score, strategic_alignment_score
```

**`pipeline_events`**
Every time a contact moves through a role stage.
```
id, contact_id, from_stage, to_stage,
date, trigger_activity_id
```

**`velocity_metrics`**
Daily snapshot of the speed program.
```
date, outreach_count, target (9–10),
tier1_touches, us_side_touches,
inmails_sent, inmails_remaining,
aaep_days_remaining
```

**`intelligence_triggers`**
AAEP developments, policy news, leadership changes, earnings calls.
```
id, date, type, description,
relevant_contact_ids, actioned (bool)
```

**`artifacts`**
Every artifact produced and its delivery status.
```
id, contact_id, type (two_pager/intelligence_brief/pptx),
produced_date, sent_date, response_received (bool),
response_date, outcome
```

**`working_group_stages`**
Defined thresholds for working group progression.
```
id, contact_id, interest_expressed_date,
offer_made_date, terms_discussed_date,
confirmed_date, quarterly_fee_status
```

---

## Pipeline Tracks

Two separate tracks — different logic, different success metrics:

**Global South Track (Tier 1 + Tier 2)**
- 6-stage role journey: Identification → Role Packet → Preparation → Buy-in → Execution → New Role Creation
- Success: activation ($25K–$75K), working group conversion, AAEP package candidacy
- Cadaver exit: no meaningful movement after defined touch sequence

**U.S.-Side Track (Tier 3)**
- Stages: Identified → Mapped → First Contact → Relationship Building → Active Collaborator
- Targets: think tanks, DC lawyers, policy community, AAEP program leaders, Silicon Valley
- Currently at zero — agent flags this every day until it changes
- Success metric: Faisal recognized as expert interlocutor for Global South telcos in AAEP design

---

## Working Group Stage Definitions

A contact advances through defined thresholds — not subjective:

| Stage | Definition |
|---|---|
| Active Lead | In outreach sequence, no working group conversation started |
| Interest Expressed | Contact has asked a question about working group or responded positively to framing |
| Offer Made | Tangier has formally described the working group and what membership involves |
| Terms Discussed | Specifics of fees, access, and cadence have been discussed |
| Confirmed Member | Commitment made, quarterly fee agreed |

---

## Narrative Engine

**Daily Brief** (every morning via email + on-demand via MCP)

Four sections in order:
1. Velocity check — outreach count vs. target, Tier 1 entities not touched in 5+ days, AAEP window countdown
2. What moved yesterday — pipeline stage changes, new commitments, responses received
3. What is at risk — overdue commitments, stalled contacts, activities that scored zero on the three tests
4. Today's priority — one action, derived from what the data says is highest-leverage

**Weekly Narrative** (Friday via email + on-demand)

Longer-form story of the week: where velocity accelerated and why, which relationships advanced, pattern recognition across contacts, strategic alignment score for the week as a whole.

**Role Journey Report** (per principal, on demand via MCP)

Where a principal sits in the 6-stage role journey, what moved them there, how long they have been at the current stage, and the next concrete action to advance them.

---

## Agent Personality: The Corridor Insider

The agent speaks like someone who has been in the room, understands what is at stake, and will not waste your time.

Rules:
- Uses Tangier's vocabulary naturally: cadaver, beachhead, corridor, trust ladder, role packet, governed operator, first-mover window
- One sentence for a win, then moves on
- Never softens a stall — names it directly, immediately says what to do
- Asks the hard question when data shows avoidance: *"U.S.-side outreach has been at zero for 14 days. The lever that makes everything else fall into line hasn't been pulled."*
- No em dashes, no filler, no hedge stacking, no AI-sounding language
- Reads like Faisal's internal monologue, not a status report
- Every sentence carries information

The master strategic context and role framework are loaded as the system prompt for every narrative generation call. This is what makes the output sound like a Tangier insider wrote it.

---

## Alert System

**Two layers:**

**Layer 1 — Session hook**
`get_alerts` runs automatically when either user opens Claude Code. Surfaces all pending alerts before anything else.

**Layer 2 — Email (both faisal@tangier.us and community@evqlabs.com)**

| Trigger | Frequency |
|---|---|
| Daily brief | Every morning |
| Weekly narrative | Every Friday |
| Tier 1 contact responds | Immediate |
| Pipeline stage change | Immediate |
| Intelligence trigger detected (AAEP news, leadership change, earnings call) | Immediate |
| Cadaver recommendation | Immediate |
| Daily outreach below target for 2 consecutive days | Immediate |
| Tier 1 entity not touched in 5+ days | Daily until resolved |
| Commitment overdue (24-hour advance warning + overdue alert) | On threshold |
| AAEP window: 60 days remaining | Once |
| AAEP window: 30 days remaining | Once |
| AAEP window: 14 days remaining | Once |
| InMail unused for 7+ days | Weekly |
| U.S.-side outreach at zero after 7 days | Daily until resolved |

---

## Multi-User Setup

Both users register the MCP on their own machines. All data goes to the same Supabase instance. Attribution is tracked via `created_by` on every activity.

Code lives on GitHub. Both can develop independently via separate branches. Any new MCP tool added by either user is announced to the other before it goes to the shared Render deployment.

---

## Seeding Plan (Before Go-Live)

The agent starts with zero memory. Before the first daily brief, the following must be loaded:

1. All contacts from the outreach database — name, company, tier, current status, last touch date
2. Historical outreach log — ~160 emails sent, LinkedIn connections made, responses received
3. Tier 1 entity statuses — where each of the 8 entities stands today
4. Open commitments — everything currently owed by or to Tangier
5. Artifact inventory — which two-pagers and intelligence briefs have been produced and sent
6. AAEP status — preset window open, 74 days remaining as of April 16, 2026
7. Master strategic context — loaded as system prompt, not as data

Seeding is done via `log_activity` in bulk or a one-time seed script. Must be complete before go-live.

---

## Granola Transcript Format

Two accepted input formats for `log_activity`:

**Format 1 — Raw Granola export**
Timestamped speaker transcript. Agent identifies: participants, commitments made, contacts referenced, activities described, decisions taken.

**Format 2 — Manual summary**
Free-form text you write yourself. Agent applies the same extraction logic. Less structured but fully supported.

Both formats produce the same output: extracted activities, commitments, contact touches, and any role stage movements.

---

## AAEP Escalation Logic

The 90-day proposal window (closes late June 2026) is the most time-sensitive external constraint.

- Below 60 days: daily brief includes AAEP countdown prominently
- Below 30 days: every brief leads with the countdown; email alert sent once
- Below 14 days: every brief opens with urgency flag; email alert sent once; `get_velocity_report` adds a dedicated AAEP section
- Day of close: final alert sent; agent begins tracking post-window positioning

---

## What This Is Not

- It does not send outreach on your behalf
- It does not make decisions — it surfaces what the data says and asks the hard question
- It does not replace the Engagement Management Agent — EMA manages individual client engagements; this agent manages Tangier's overall operational velocity
- It is not a dashboard — it is a conversation partner that happens to have perfect memory
