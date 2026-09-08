-- FindBack AI — Phase 1 initial schema
-- Run this in the Supabase SQL editor (or via psql against DATABASE_URL).
-- Mirrors Architecture.md Section 5 (Data Model).

create extension if not exists "pgvector";
create extension if not exists "uuid-ossp";

-- ---------------------------------------------------------------------
-- Users (profile row linked 1:1 with Supabase auth.users.id in production)
-- ---------------------------------------------------------------------
create table if not exists users (
    id uuid primary key default uuid_generate_v4(),
    email text unique not null,
    name text,
    role text not null default 'User' check (role in ('User', 'Admin')),
    created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- Reports
-- ---------------------------------------------------------------------
create table if not exists reports (
    id uuid primary key default uuid_generate_v4(),
    user_id uuid not null references users(id) on delete cascade,
    type text not null check (type in ('LOST', 'FOUND')),
    title text not null,
    category text not null,
    color text not null,
    brand text,
    description text not null,
    features text,
    location text not null,
    report_date date not null,
    report_time time,
    status text not null,
    image_urls text[] not null default '{}',
    image_embedding vector(512),
    text_embedding vector(384),
    is_active text not null default 'true',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_reports_type_status on reports (type, is_active);
create index if not exists idx_reports_category on reports (category);
create index if not exists idx_reports_user on reports (user_id);

-- Approximate nearest-neighbor indexes — see migrations/003_vector_indexes.sql
-- (Phase 5). Left out of this initial migration since they only pay off
-- once report volume is non-trivial (Architecture Sec. 12).

-- ---------------------------------------------------------------------
-- Matches
-- ---------------------------------------------------------------------
create table if not exists matches (
    id uuid primary key default uuid_generate_v4(),
    lost_report_id uuid not null references reports(id) on delete cascade,
    found_report_id uuid not null references reports(id) on delete cascade,
    image_score float not null default 0,
    text_score float not null default 0,
    category_score float not null default 0,
    color_score float not null default 0,
    brand_score float not null default 0,
    location_score float not null default 0,
    time_score float not null default 0,
    other_score float not null default 0,
    final_score float not null default 0,
    explanation text[] not null default '{}',
    created_at timestamptz not null default now()
);

create index if not exists idx_matches_final_score on matches (final_score desc);
create index if not exists idx_matches_lost on matches (lost_report_id);
create index if not exists idx_matches_found on matches (found_report_id);

-- ---------------------------------------------------------------------
-- Notifications
-- ---------------------------------------------------------------------
create table if not exists notifications (
    id uuid primary key default uuid_generate_v4(),
    user_id uuid not null references users(id) on delete cascade,
    match_id uuid not null references matches(id) on delete cascade,
    title text not null,
    message text not null,
    is_read boolean not null default false,
    created_at timestamptz not null default now()
);

create index if not exists idx_notifications_user on notifications (user_id, is_read);

-- ---------------------------------------------------------------------
-- Row Level Security (enable + baseline policies; refine per SRS Sec. 7)
-- ---------------------------------------------------------------------
alter table reports enable row level security;
alter table matches enable row level security;
alter table notifications enable row level security;

-- Users can read/write only their own reports; admins bypass via service role.
create policy if not exists reports_select_own on reports
    for select using (auth.uid() = user_id or true); -- public metadata readable (SRS FR: "search/browse public report metadata")

create policy if not exists reports_modify_own on reports
    for update using (auth.uid() = user_id);

create policy if not exists reports_delete_own on reports
    for delete using (auth.uid() = user_id);

create policy if not exists notifications_select_own on notifications
    for select using (auth.uid() = user_id);

create policy if not exists notifications_update_own on notifications
    for update using (auth.uid() = user_id);
