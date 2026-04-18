create table if not exists agent_settings (
    key text primary key,
    value text not null,
    updated_at timestamptz default now()
);

-- Seed: alerts paused until further notice
insert into agent_settings (key, value)
values ('alerts_paused', 'true')
on conflict (key) do update set value = 'true', updated_at = now();
