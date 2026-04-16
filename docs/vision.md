# Progress Tracking & Narrative Agent — Vision & Roadmap

## The Problem This Solves

Faisal and Aftab are running a high-velocity outreach program across 300+ contacts while simultaneously managing active engagements, producing artifacts, and building U.S.-side credibility. The risk is not lack of effort — it is **task-jumping, context-switching, and things slipping through the cracks**.

Without a system:
- Commitments made in calls get forgotten
- No one knows what moved yesterday vs. what stalled
- Faisal and Aftab operate from separate mental models of the same reality
- Momentum is invisible until it's gone

The agent exists to solve this. It is the **automated chief of staff** that never forgets, never loses context, and narrates what's happening so both people always share the same picture.

---

## The Full Vision (At Maturity)

An agent that:

- **Ingests activity from everywhere** — Granola transcripts, Telegram conversations, GitHub notes, typed updates — automatically, without manual effort
- **Maintains genuine organizational memory** — knows what happened with Banglalink in week 3, what the pattern was with Ncell, who responds on Mondays, who went cold after the first message
- **Generates daily narratives** — not a dashboard, not a table — a story. What moved. What stalled. What needs attention in the next 24 hours. Written in Tangier's voice.
- **Holds both people accountable** — every commitment is tracked, every deadline is flagged, every overdue item surfaces automatically
- **Scores activity against strategic intent** — not all activity is equal; the agent knows the three tests and flags effort that doesn't pass any of them
- **Detects patterns** — "Tier 1 contacts respond better after a U.S. press mention" or "InMail is outperforming cold email by 3x this month"
- **Alerts proactively** — doesn't wait to be asked; emails when something is overdue, stalled, or at risk

At full maturity, neither Faisal nor Aftab needs to track anything manually. They log activity, the agent handles the rest.

---

## Current State — Phase 1 (Live)

**What's built and working:**

- MCP server deployed on Render, registered on Aftab's Claude Code
- Supabase database with 10 tables + pgvector semantic memory
- 10 MCP tools accessible from Claude Code terminal
- Email alerts via Brevo (daily brief at 10am Bangladesh time, alert checks every 2 hours)
- Active pipeline: Banglalink, Orange Maroc, Ncell (seeded)
- All other Tier 1 contacts seeded: e&, Omantel, QAI, Ooredoo, Zain, STC, Humain, G42

**How you use it today:**
- After every meaningful call or update — paste the transcript or notes into `log_activity`
- Start of every Claude Code session — `get_alerts` shows what needs attention
- Weekly review with Faisal — `get_velocity_report` + `get_pipeline_snapshot`
- Commitments made in calls — `add_commitment` immediately
- 10am Bangladesh time — daily brief lands in both inboxes automatically

---

## Roadmap

### Phase 2 — GitHub Integration
**What:** Pull meeting notes and updates directly from your GitHub repos without pasting manually.

**Tool to add:** `pull_github_notes`

**Why now:** GitHub CLI is already part of the workflow. This eliminates one manual step.

---

### Phase 3 — Granola Transcript Ingestion
**What:** Granola saves meeting transcripts automatically. Instead of copying and pasting, the agent pulls them directly.

**Requires:** Granola API access or file-based integration.

**Impact:** The biggest reduction in manual effort. Every meeting auto-logged.

---

### Phase 4 — Telegram Analysis
**What:** Faisal and contacts communicate on Telegram. The agent reads those threads and extracts activities, signals, and commitments.

**Requires:** Telegram API integration, possibly Claude computer use for parsing.

**Impact:** Nothing slips. Every channel is covered.

---

### Phase 5 — Pattern Intelligence (Full Maturity)
**What:** The agent stops just recording and starts noticing. Identifies response patterns by contact, channel, timing. Surfaces what's working and what isn't. Predictive accountability.

**Examples:**
- "Tier 1 contacts touched less than once per 2 weeks have a 70% stall rate"
- "Artifacts sent on Tuesday get 2x response rate vs. Friday"
- "Michael responds within 48 hours when outreach references AAEP specifically"

**Impact:** Execution becomes smarter over time, not just faster.

---

## Success Criteria

- **2 closes per month minimum** — the agent keeps outreach velocity visible so this target is never missed silently
- **Zero forgotten commitments** — every promise made is tracked and surfaces before it goes overdue
- **Both Faisal and Aftab always share the same picture** — no separate mental models, no "I thought you handled that"
- **9–10 outreach activities per 24-hour period** tracked and visible
- **Activity scoring keeps effort honest** — if something doesn't pass the three strategic tests, it gets flagged before time is wasted

---

## The Three Strategic Tests

Every activity is scored against these. An activity scoring zero on all three gets flagged.

1. **Does it make outreach more effective?** (better targeting, better artifacts, better sequencing)
2. **Does it advance a Tier 1 relationship?** (moves a principal forward in the 6-stage journey)
3. **Does it build U.S.-side credibility?** (connects Tangier to the U.S. network that matters for AAEP)

---

## Technology Stack Notes

**Current stack:** Python + FastAPI + Starlette + Supabase + pgvector + Claude API + OpenAI embeddings + Brevo + APScheduler + MCP SSE

**What was considered but deferred:**
- **mem0** — purpose-built AI memory layer; would replace the manual pgvector setup. Revisit in Phase 3 when memory retrieval needs to become more sophisticated.
- **LangGraph** — stateful agent orchestration with built-in checkpointing. Revisit in Phase 5 when multi-step autonomous workflows are needed.
- **Dashboard UI** — terminal-first is the right call for now; revisit if the team grows beyond Faisal and Aftab.

---

## For Future Claude Code Sessions

When picking up this project, start here:
1. Check current phase against this document
2. Run `get_alerts` to see current state
3. Ask: "what's the next Phase X item to build?"

The vision is intact. Build it one phase at a time.
