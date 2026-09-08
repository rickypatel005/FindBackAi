-- FindBack AI — Phase 5 (Search & Matching): approximate nearest-neighbor
-- indexes for the pgvector candidate-narrowing query added in
-- app/services/matching.py (_vector_prefilter_candidates, SRS FR-07.2).
--
-- These are OPTIONAL and safe to run at any time, but only pay off once
-- `reports` has a non-trivial number of rows — on a small/empty table an
-- IVFFlat index adds overhead without a meaningful speedup, since pgvector
-- happily falls back to an exact scan either way (see Architecture Sec. 12
-- and matching.py's docstring on this exact tradeoff).
--
-- `lists` is a rough starting point (~sqrt(row_count) is the usual rule of
-- thumb); revisit once you know real demo-data volume. Run this manually
-- against your Supabase/Postgres instance when ready:
--   psql "$DATABASE_URL" -f backend/migrations/003_vector_indexes.sql

create index if not exists idx_reports_image_embedding
    on reports using ivfflat (image_embedding vector_cosine_ops)
    with (lists = 100);

create index if not exists idx_reports_text_embedding
    on reports using ivfflat (text_embedding vector_cosine_ops)
    with (lists = 100);

-- After creating (or rebuilding) these indexes, running ANALYZE lets the
-- planner pick up the new statistics immediately rather than waiting for
-- autovacuum.
analyze reports;
