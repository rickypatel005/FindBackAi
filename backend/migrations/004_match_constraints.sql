-- FindBack AI — Phase 6 (Explainability & Notifications) hardening.
--
-- Prior to Phase 6, POST /matches/find/{report_id} always INSERTed a fresh
-- row per candidate pair, so re-running it (e.g. after a user edits report
-- text, or simply re-opens "Check for matches") produced duplicate Match
-- rows for the same lost/found pair and re-fired a notification every time
-- the pair scored at/above the threshold — spamming both owners on every
-- click. app/services/matching.py::find_and_persist_matches now upserts by
-- (lost_report_id, found_report_id) in application code; this constraint is
-- the DB-level backstop so that invariant holds even under concurrent
-- requests.
--
-- Run manually against your Supabase/Postgres instance:
--   psql "$DATABASE_URL" -f backend/migrations/004_match_constraints.sql

alter table matches
    add column if not exists updated_at timestamptz not null default now();

-- If earlier runs (pre-Phase-6) already produced duplicate rows for the
-- same pair, keep only the most recently updated one before the unique
-- constraint can be added.
delete from matches m
    using matches newer
    where m.lost_report_id = newer.lost_report_id
      and m.found_report_id = newer.found_report_id
      and m.created_at < newer.created_at;

alter table matches
    add constraint uq_matches_lost_found unique (lost_report_id, found_report_id);
