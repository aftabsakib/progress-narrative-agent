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

-- Agent settings: key-value store for runtime configuration
create table if not exists agent_settings (
    key text primary key,
    value text not null,
    updated_at timestamptz default now()
);

-- Indexes
create index on activities using ivfflat (embedding vector_cosine_ops) with (lists = 100);
create index on activities (date desc);
create index on contacts (tier, status);
create index on commitments (status, due_date);
create index on alerts (actioned, created_at desc);

-- pgvector similarity function for semantic retrieval
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
